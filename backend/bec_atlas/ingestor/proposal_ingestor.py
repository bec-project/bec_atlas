import datetime

import pymongo
import requests

from bec_atlas.model import Experiment, is_valid_beamline_name, name_to_xname


class ProposalIngestor:

    def __init__(
        self,
        duo_token: str,
        mongodb_host: str = "localhost",
        mongodb_port: int = 27017,
        redis_host: str = "localhost",
        redis_port: int = 6380,
        duo_base_url: str = "https://duo.psi.ch/duo/api.php/v1",
    ):
        self.client = pymongo.MongoClient(mongodb_host, mongodb_port)
        self.db = self.client["bec_atlas"]
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.duo_base_url = duo_base_url
        self.duo_header = {"X-API-SECRET": duo_token}
        self.realms_by_xname = {}
        self.facilities = ["sls"]
        self._update_xnames()

    def load_proposals_from_duo(self, full: bool = False) -> dict:
        """
        Load proposals from the DUO API.
        """
        if full:
            data = self._fetch_all_proposals()
        else:
            data = self._fetch_all_proposals(years=datetime.datetime.now().year)

        return data

    def ingest_to_mongo(self, data: dict) -> str:
        """
        Ingest proposal data into MongoDB.

        Returns:
           str: The ID of the last inserted pgroup.
        """
        inserted_pgroup = []
        for item in data.values():
            if not item.pgroup:
                continue
            item._id = item.pgroup
            existing_exp = self.db["experiments"].find_one({"_id": item._id})
            if existing_exp:
                existing_exp = Experiment(**existing_exp)
                input_exp = item.model_dump()
                reference_exp = existing_exp.model_dump()
                for key in ["id", "pgroup"]:
                    input_exp.pop(key, None)
                    reference_exp.pop(key, None)
                if input_exp != reference_exp:
                    self.db["experiments"].update_one({"_id": item._id}, {"$set": item.__dict__})
                continue
            result = self.db["experiments"].insert_one(item.__dict__)
            inserted_pgroup.append(item.pgroup)

        return sorted(inserted_pgroup)[-1] if inserted_pgroup else ""

    def _update_xnames(self):
        """
        Update the xnames mapping.
        """
        realms = self.db["realms"].find(projection={"realm_id": 1, "xname": 1, "managers": 1})
        for realm in realms:
            if not realm.get("xname"):
                continue
            self.realms_by_xname[realm["xname"]] = {
                "realm_id": realm["realm_id"],
                "managers": realm["managers"],
            }

    def _fetch_all_proposals(self, years: list[int] | int | None = None) -> dict:
        """
        Fetch all proposals from the DUO API for the last ten years.
        If a year is specified, only proposals for that year are fetched.
        """
        if years is None:
            # last ten years
            years = sorted([datetime.datetime.now().year - i for i in range(10)])
        elif not isinstance(years, list):
            years = [years]

        data = {}
        data.update(self._fetch_proposals(years=years))

        data.update(self._fetch_pgroups_without_proposal(years=years))

        return data

    def _fetch_proposals(self, years: list[int] | None) -> dict:
        out = {}
        for facility in self.facilities:
            for year in years:
                url = f"{self.duo_base_url}/CalendarInfos/proposals/{facility}"
                params = {"year": year} if year is not None else None
                response = requests.get(url, params=params, headers=self.duo_header, timeout=5)
                response.raise_for_status()
                data = response.json()
                for item in data:
                    if item["proposal"]:
                        if not is_valid_beamline_name(item["beamline"]):
                            continue
                        xname = name_to_xname(item["beamline"])
                        if xname not in self.realms_by_xname:
                            continue

                        item["owner_groups"] = ["admin"]
                        item["access_groups"] = self.realms_by_xname[xname]["managers"]
                        item["realm_id"] = item.pop("beamline")
                        exp = Experiment(**item)
                        out[item["proposal"]] = exp

        return out

    def _fetch_pgroups_without_proposal(self, years: list[int]) -> dict:
        year = min(years) if years else datetime.datetime.now().year
        url = f"{self.duo_base_url}/PGroupAttributes/listProposalAssignments"
        params = {"withoutproposal": "true", "createdsince": f"{year}-01-01"}
        response = requests.get(url, headers=self.duo_header, params=params, timeout=10)
        response.raise_for_status()
        pgroups_wo_proposal = [item["g"] for item in response.json()]

        out = {}
        for pgroup in pgroups_wo_proposal:
            pgroup_info = self._fetch_proposal_details(pgroup)
            xname = pgroup_info.get("xname")
            if not xname:
                continue
            xname = xname.lower()
            if xname not in self.realms_by_xname:
                continue
            out[pgroup] = Experiment(
                owner_groups=["admin"],
                access_groups=self.realms_by_xname[xname]["managers"],
                realm_id=xname,
                proposal="",
                title=pgroup,
                firstname=pgroup_info.get("owner", {}).get("firstname", "") or "",
                lastname=pgroup_info.get("owner", {}).get("lastname", "") or "",
                email=pgroup_info.get("owner", {}).get("email", "") or "",
                account=pgroup_info.get("owner", {}).get("adaccount", {}).get("username", "") or "",
                pi_firstname="",
                pi_lastname="",
                pi_email="",
                pi_account="",
                eaccount=pgroup.replace("p", "e"),
                pgroup=pgroup,
                abstract=pgroup_info.get("comments", "") or "",
            )

        return out

    def _fetch_proposal_details(self, pgroup):
        """
        Fetch proposal details for a specific PGroup.
        """
        url = f"{self.duo_base_url}/CalendarInfos/pgroup/{pgroup}"
        response = requests.get(url, headers=self.duo_header, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["group"]


if __name__ == "__main__":
    import os

    import dotenv

    import bec_atlas

    bec_atlas_path = os.path.dirname(os.path.dirname(os.path.dirname(bec_atlas.__file__)))
    val = dotenv.dotenv_values(os.path.join(bec_atlas_path, ".duo.env"))
    duo_token = val.get("TOKEN")
    if not duo_token:
        raise RuntimeError("DUO token not found in .duo.env file")
    proposal_ingestor = ProposalIngestor(duo_token=duo_token)
    experiments = proposal_ingestor.load_proposals_from_duo(full=True)
    last_pgroup = proposal_ingestor.ingest_to_mongo(experiments)
    print(f"Last inserted pgroup: {last_pgroup}")
