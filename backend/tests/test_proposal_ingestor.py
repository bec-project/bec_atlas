import datetime
from unittest import mock

import mongomock
import pytest

from bec_atlas.ingestor.proposal_ingestor import ProposalIngestor
from bec_atlas.model.model import Experiment


@pytest.fixture
def proposal_ingestor():
    """Create a ProposalIngestor instance with mock MongoDB."""
    with mock.patch("pymongo.MongoClient") as mock_client:
        mock_client.return_value = mongomock.MongoClient("localhost", 27017)
        ingestor = ProposalIngestor(
            duo_token="test_token",
            mongodb_host="localhost",
            mongodb_port=27017,
            duo_base_url="https://test.duo.psi.ch/duo/api.php/v1",
        )
        # Setup some test realms data
        ingestor.db["realms"].insert_many(
            [
                {
                    "_id": "x12sa",
                    "realm_id": "cSAXS",
                    "xname": "x12sa",
                    "managers": ["unx-sls_x12sa_bs"],
                },
                {
                    "_id": "x01da",
                    "realm_id": "Debye",
                    "xname": "x01da",
                    "managers": ["unx-sls_x01da_bs"],
                },
            ]
        )
        ingestor._update_xnames()
        return ingestor


@pytest.fixture
def sample_duo_proposals_response():
    """Sample response from DUO proposals API."""
    return [
        {
            "proposal": "20240001",
            "title": "Test Proposal 1",
            "beamline": "cSAXS",
            "firstname": "John",
            "lastname": "Doe",
            "email": "john.doe@example.com",
            "account": "jdoe",
            "pi_firstname": "Jane",
            "pi_lastname": "Smith",
            "pi_email": "jane.smith@example.com",
            "pi_account": "jsmith",
            "eaccount": "e20240001",
            "pgroup": "p20240001",
            "abstract": "This is a test proposal",
            "schedule": None,
            "proposal_submitted": "2024-01-01",
            "proposal_expire": "2024-12-31",
            "proposal_status": "approved",
            "delta_last_schedule": 0,
            "mainproposal": None,
        },
        {
            "proposal": "20240002",
            "title": "Test Proposal 2",
            "beamline": "Debye",
            "firstname": "Alice",
            "lastname": "Johnson",
            "email": "alice.johnson@example.com",
            "account": "ajohnson",
            "pi_firstname": "Bob",
            "pi_lastname": "Wilson",
            "pi_email": "bob.wilson@example.com",
            "pi_account": "bwilson",
            "eaccount": "e20240002",
            "pgroup": "p20240002",
            "abstract": "Another test proposal",
            "schedule": [],
            "proposal_submitted": "2024-02-01",
            "proposal_expire": "2024-12-31",
            "proposal_status": "approved",
            "delta_last_schedule": 5,
            "mainproposal": "20240001",
        },
        {
            "proposal": "",
            "title": "No Proposal Number",
            "beamline": "cSAXS",
            "firstname": "Test",
            "lastname": "User",
            "email": "test@example.com",
            "account": "test",
            "pi_firstname": "",
            "pi_lastname": "",
            "pi_email": "",
            "pi_account": "",
            "eaccount": "",
            "pgroup": "p20240003",
            "abstract": "",
            "schedule": None,
            "proposal_submitted": None,
            "proposal_expire": None,
            "proposal_status": None,
            "delta_last_schedule": None,
            "mainproposal": None,
        },
    ]


@pytest.fixture
def sample_pgroup_details_response():
    """Sample response from DUO pgroup details API."""
    return {
        "group": {
            "xname": "x12sa",
            "comments": "Test pgroup without proposal",
            "owner": {
                "firstname": "Test",
                "lastname": "Owner",
                "email": "test.owner@example.com",
                "adaccount": {"username": "towner"},
            },
        }
    }


@pytest.fixture
def sample_pgroups_without_proposal_response():
    """Sample response from DUO pgroups without proposal API."""
    return [{"g": "p20240010"}, {"g": "p20240011"}]


@pytest.mark.timeout(60)
def test_proposal_ingestor_init():
    """Test ProposalIngestor initialization."""
    with mock.patch("pymongo.MongoClient") as mock_client:
        mock_client.return_value = mongomock.MongoClient("localhost", 27017)

        ingestor = ProposalIngestor(
            duo_token="test_token",
            mongodb_host="localhost",
            mongodb_port=27017,
            redis_host="localhost",
            redis_port=6380,
            duo_base_url="https://test.duo.psi.ch/duo/api.php/v1",
        )

        assert ingestor.duo_base_url == "https://test.duo.psi.ch/duo/api.php/v1"
        assert ingestor.duo_header == {"X-API-SECRET": "test_token"}
        assert ingestor.redis_host == "localhost"
        assert ingestor.redis_port == 6380
        assert ingestor.facilities == ["sls"]


@pytest.mark.timeout(60)
def test_update_xnames(proposal_ingestor):
    """Test xnames mapping update."""
    assert "x12sa" in proposal_ingestor.realms_by_xname
    assert "x01da" in proposal_ingestor.realms_by_xname

    assert proposal_ingestor.realms_by_xname["x12sa"]["realm_id"] == "cSAXS"
    assert proposal_ingestor.realms_by_xname["x12sa"]["managers"] == ["unx-sls_x12sa_bs"]

    assert proposal_ingestor.realms_by_xname["x01da"]["realm_id"] == "Debye"
    assert proposal_ingestor.realms_by_xname["x01da"]["managers"] == ["unx-sls_x01da_bs"]


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_fetch_proposals(mock_requests_get, proposal_ingestor, sample_duo_proposals_response):
    """Test fetching proposals from DUO API."""
    mock_response = mock.Mock()
    mock_response.json.return_value = sample_duo_proposals_response
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    proposals = proposal_ingestor._fetch_proposals([2024])

    assert len(proposals) == 2  # Only proposals with proposal numbers
    assert "20240001" in proposals
    assert "20240002" in proposals

    # Check proposal details
    proposal_1 = proposals["20240001"]
    assert isinstance(proposal_1, Experiment)
    assert proposal_1.title == "Test Proposal 1"
    assert proposal_1.realm_id == "cSAXS"
    assert proposal_1.owner_groups == ["admin"]
    assert proposal_1.access_groups == ["unx-sls_x12sa_bs"]


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_fetch_proposals_invalid_beamline(mock_requests_get, proposal_ingestor):
    """Test fetching proposals with invalid beamline names."""
    invalid_response = [
        {
            "proposal": "20240001",
            "title": "Invalid Beamline Proposal",
            "beamline": "InvalidBeamline",
            "firstname": "John",
            "lastname": "Doe",
            "email": "john.doe@example.com",
            "account": "jdoe",
            "pi_firstname": "Jane",
            "pi_lastname": "Smith",
            "pi_email": "jane.smith@example.com",
            "pi_account": "jsmith",
            "eaccount": "e20240001",
            "pgroup": "p20240001",
            "abstract": "This proposal has invalid beamline",
        }
    ]

    mock_response = mock.Mock()
    mock_response.json.return_value = invalid_response
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    proposals = proposal_ingestor._fetch_proposals([2024])

    assert len(proposals) == 0  # Should be empty due to invalid beamline


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_fetch_pgroups_without_proposal(
    mock_requests_get,
    proposal_ingestor,
    sample_pgroups_without_proposal_response,
    sample_pgroup_details_response,
):
    """Test fetching pgroups without proposals."""
    # Mock the list pgroups call
    mock_list_response = mock.Mock()
    mock_list_response.json.return_value = sample_pgroups_without_proposal_response
    mock_list_response.raise_for_status.return_value = None

    # Mock the pgroup details call
    mock_details_response = mock.Mock()
    mock_details_response.json.return_value = sample_pgroup_details_response
    mock_details_response.raise_for_status.return_value = None

    # Configure the mock to return different responses for different URLs
    def side_effect(url, **kwargs):
        if "listProposalAssignments" in url:
            return mock_list_response
        elif "pgroup/" in url:
            return mock_details_response
        return mock.Mock()

    mock_requests_get.side_effect = side_effect

    pgroups = proposal_ingestor._fetch_pgroups_without_proposal([2024])

    assert len(pgroups) == 2
    assert "p20240010" in pgroups
    assert "p20240011" in pgroups

    # Check pgroup details
    pgroup_exp = pgroups["p20240010"]
    assert isinstance(pgroup_exp, Experiment)
    assert pgroup_exp.proposal == ""
    assert pgroup_exp.title == "p20240010"
    assert (
        pgroup_exp.realm_id == "cSAXS"
    )  # The actual implementation seems to use the realm_id from mapping
    assert pgroup_exp.firstname == "Test"
    assert pgroup_exp.lastname == "Owner"
    assert pgroup_exp.email == "test.owner@example.com"
    assert pgroup_exp.account == "towner"
    assert pgroup_exp.eaccount == "e20240010"
    assert pgroup_exp.abstract == "Test pgroup without proposal"


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_fetch_proposal_details(
    mock_requests_get, proposal_ingestor, sample_pgroup_details_response
):
    """Test fetching details for a specific pgroup."""
    mock_response = mock.Mock()
    mock_response.json.return_value = sample_pgroup_details_response
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    details = proposal_ingestor._fetch_proposal_details("p20240010")

    assert details["xname"] == "x12sa"
    assert details["comments"] == "Test pgroup without proposal"
    assert details["owner"]["firstname"] == "Test"
    assert details["owner"]["lastname"] == "Owner"


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_load_proposals_from_duo_full(mock_requests_get, proposal_ingestor):
    """Test loading all proposals from DUO."""
    mock_response = mock.Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    with mock.patch.object(proposal_ingestor, "_fetch_all_proposals") as mock_fetch:
        mock_fetch.return_value = {"test": "data"}

        result = proposal_ingestor.load_proposals_from_duo(full=True)

        mock_fetch.assert_called_once_with()
        assert result == {"test": "data"}


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_load_proposals_from_duo_current_year(mock_requests_get, proposal_ingestor):
    """Test loading proposals from DUO for current year only."""
    mock_response = mock.Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    with mock.patch.object(proposal_ingestor, "_fetch_all_proposals") as mock_fetch:
        mock_fetch.return_value = {"test": "data"}

        result = proposal_ingestor.load_proposals_from_duo(full=False)

        mock_fetch.assert_called_once_with(years=datetime.datetime.now().year)
        assert result == {"test": "data"}


@pytest.mark.timeout(60)
def test_ingest_to_mongo_new_experiments(proposal_ingestor):
    """Test ingesting new experiments to MongoDB."""
    # Create test experiments
    exp1 = Experiment(
        owner_groups=["admin"],
        access_groups=["test_group"],
        realm_id="cSAXS",
        proposal="20240001",
        title="Test Experiment 1",
        firstname="John",
        lastname="Doe",
        email="john.doe@example.com",
        account="jdoe",
        pi_firstname="Jane",
        pi_lastname="Smith",
        pi_email="jane.smith@example.com",
        pi_account="jsmith",
        eaccount="e20240001",
        pgroup="p20240001",
        abstract="Test abstract",
    )

    exp2 = Experiment(
        owner_groups=["admin"],
        access_groups=["test_group"],
        realm_id="Debye",
        proposal="20240002",
        title="Test Experiment 2",
        firstname="Alice",
        lastname="Johnson",
        email="alice.johnson@example.com",
        account="ajohnson",
        pi_firstname="Bob",
        pi_lastname="Wilson",
        pi_email="bob.wilson@example.com",
        pi_account="bwilson",
        eaccount="e20240002",
        pgroup="p20240002",
        abstract="Another test abstract",
    )

    data = {"20240001": exp1, "20240002": exp2}

    last_pgroup = proposal_ingestor.ingest_to_mongo(data)

    assert last_pgroup == "p20240002"

    # Check that experiments were inserted
    assert proposal_ingestor.db["experiments"].count_documents({}) == 2

    stored_exp1 = proposal_ingestor.db["experiments"].find_one({"_id": "p20240001"})
    assert stored_exp1 is not None
    assert stored_exp1["title"] == "Test Experiment 1"

    stored_exp2 = proposal_ingestor.db["experiments"].find_one({"_id": "p20240002"})
    assert stored_exp2 is not None
    assert stored_exp2["title"] == "Test Experiment 2"


@pytest.mark.timeout(60)
def test_ingest_to_mongo_skip_no_pgroup(proposal_ingestor):
    """Test that experiments without pgroup are skipped."""
    exp_no_pgroup = Experiment(
        owner_groups=["admin"],
        access_groups=["test_group"],
        realm_id="cSAXS",
        proposal="20240001",
        title="No PGroup",
        firstname="John",
        lastname="Doe",
        email="john.doe@example.com",
        account="jdoe",
        pi_firstname="Jane",
        pi_lastname="Smith",
        pi_email="jane.smith@example.com",
        pi_account="jsmith",
        eaccount="e20240001",
        pgroup="",  # Empty pgroup
        abstract="Test abstract",
    )

    data = {"20240001": exp_no_pgroup}

    last_pgroup = proposal_ingestor.ingest_to_mongo(data)

    assert last_pgroup == ""
    assert proposal_ingestor.db["experiments"].count_documents({}) == 0


@pytest.mark.timeout(60)
def test_ingest_to_mongo_update_existing(proposal_ingestor):
    """Test updating existing experiments in MongoDB."""
    # Insert initial experiment
    initial_exp = Experiment(
        owner_groups=["admin"],
        access_groups=["test_group"],
        realm_id="cSAXS",
        proposal="20240001",
        title="Original Title",
        firstname="John",
        lastname="Doe",
        email="john.doe@example.com",
        account="jdoe",
        pi_firstname="Jane",
        pi_lastname="Smith",
        pi_email="jane.smith@example.com",
        pi_account="jsmith",
        eaccount="e20240001",
        pgroup="p20240001",
        abstract="Original abstract",
    )
    initial_exp._id = initial_exp.pgroup  # type: ignore
    proposal_ingestor.db["experiments"].insert_one(initial_exp.__dict__)

    # Create updated experiment
    updated_exp = Experiment(
        owner_groups=["admin"],
        access_groups=["test_group"],
        realm_id="cSAXS",
        proposal="20240001",
        title="Updated Title",  # Changed
        firstname="John",
        lastname="Doe",
        email="john.doe@example.com",
        account="jdoe",
        pi_firstname="Jane",
        pi_lastname="Smith",
        pi_email="jane.smith@example.com",
        pi_account="jsmith",
        eaccount="e20240001",
        pgroup="p20240001",
        abstract="Updated abstract",  # Changed
    )

    data = {"20240001": updated_exp}

    last_pgroup = proposal_ingestor.ingest_to_mongo(data)

    assert last_pgroup == ""  # No new insertions

    # Check that experiment was updated
    stored_exp = proposal_ingestor.db["experiments"].find_one({"_id": "p20240001"})
    assert stored_exp["title"] == "Updated Title"
    assert stored_exp["abstract"] == "Updated abstract"


@pytest.mark.timeout(60)
def test_ingest_to_mongo_no_update_if_same(proposal_ingestor):
    """Test that identical experiments are not updated."""
    # Insert initial experiment
    initial_exp = Experiment(
        owner_groups=["admin"],
        access_groups=["test_group"],
        realm_id="cSAXS",
        proposal="20240001",
        title="Test Title",
        firstname="John",
        lastname="Doe",
        email="john.doe@example.com",
        account="jdoe",
        pi_firstname="Jane",
        pi_lastname="Smith",
        pi_email="jane.smith@example.com",
        pi_account="jsmith",
        eaccount="e20240001",
        pgroup="p20240001",
        abstract="Test abstract",
    )
    initial_exp._id = initial_exp.pgroup  # type: ignore
    proposal_ingestor.db["experiments"].insert_one(initial_exp.__dict__)

    # Create identical experiment
    same_exp = Experiment(
        owner_groups=["admin"],
        access_groups=["test_group"],
        realm_id="cSAXS",
        proposal="20240001",
        title="Test Title",  # Same
        firstname="John",
        lastname="Doe",
        email="john.doe@example.com",
        account="jdoe",
        pi_firstname="Jane",
        pi_lastname="Smith",
        pi_email="jane.smith@example.com",
        pi_account="jsmith",
        eaccount="e20240001",
        pgroup="p20240001",
        abstract="Test abstract",  # Same
    )

    data = {"20240001": same_exp}

    with mock.patch.object(proposal_ingestor.db["experiments"], "update_one") as mock_update:
        last_pgroup = proposal_ingestor.ingest_to_mongo(data)

        # Should not call update since data is identical
        mock_update.assert_not_called()
        assert last_pgroup == ""


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_fetch_all_proposals_default_years(mock_requests_get, proposal_ingestor):
    """Test fetching all proposals with default years (last 10 years)."""
    mock_response = mock.Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    with (
        mock.patch.object(
            proposal_ingestor, "_fetch_proposals", return_value={}
        ) as mock_fetch_proposals,
        mock.patch.object(
            proposal_ingestor, "_fetch_pgroups_without_proposal", return_value={}
        ) as mock_fetch_pgroups,
    ):

        result = proposal_ingestor._fetch_all_proposals()

        # Should call with last 10 years
        expected_years = sorted([datetime.datetime.now().year - i for i in range(10)])
        mock_fetch_proposals.assert_called_once_with(years=expected_years)
        mock_fetch_pgroups.assert_called_once_with(years=expected_years)


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_fetch_all_proposals_specific_year(mock_requests_get, proposal_ingestor):
    """Test fetching all proposals for a specific year."""
    mock_response = mock.Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    with (
        mock.patch.object(
            proposal_ingestor, "_fetch_proposals", return_value={}
        ) as mock_fetch_proposals,
        mock.patch.object(
            proposal_ingestor, "_fetch_pgroups_without_proposal", return_value={}
        ) as mock_fetch_pgroups,
    ):

        result = proposal_ingestor._fetch_all_proposals(years=2023)

        mock_fetch_proposals.assert_called_once_with(years=[2023])
        mock_fetch_pgroups.assert_called_once_with(years=[2023])


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_requests_error_handling(mock_requests_get, proposal_ingestor):
    """Test that HTTP errors are properly handled."""
    mock_response = mock.Mock()
    mock_response.raise_for_status.side_effect = Exception("HTTP Error")
    mock_requests_get.return_value = mock_response

    with pytest.raises(Exception, match="HTTP Error"):
        proposal_ingestor._fetch_proposals([2024])


@pytest.mark.timeout(60)
def test_empty_data_ingest(proposal_ingestor):
    """Test ingesting empty data."""
    result = proposal_ingestor.ingest_to_mongo({})

    assert result == ""
    assert proposal_ingestor.db["experiments"].count_documents({}) == 0


@pytest.mark.timeout(60)
@mock.patch("requests.get")
def test_realistic_integration_flow(
    mock_requests_get,
    proposal_ingestor,
    sample_duo_proposals_response,
    sample_pgroups_without_proposal_response,
    sample_pgroup_details_response,
):
    """Test a realistic integration flow from API to database."""

    # Mock the API responses
    def side_effect(url, **kwargs):
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None

        if "proposals/" in url:
            mock_response.json.return_value = sample_duo_proposals_response
        elif "listProposalAssignments" in url:
            mock_response.json.return_value = sample_pgroups_without_proposal_response
        elif "pgroup/" in url:
            mock_response.json.return_value = sample_pgroup_details_response
        else:
            mock_response.json.return_value = []

        return mock_response

    mock_requests_get.side_effect = side_effect

    # Load proposals from DUO
    data = proposal_ingestor.load_proposals_from_duo(full=False)

    # Should have proposals + pgroups without proposals
    assert len(data) >= 2  # At least the valid proposals

    # Ingest to MongoDB
    last_pgroup = proposal_ingestor.ingest_to_mongo(data)

    # Check that data was ingested
    experiments_count = proposal_ingestor.db["experiments"].count_documents({})
    assert experiments_count > 0

    # Verify specific experiment details
    exp = proposal_ingestor.db["experiments"].find_one({"proposal": "20240001"})
    assert exp is not None
    assert exp["title"] == "Test Proposal 1"
    assert exp["realm_id"] == "cSAXS"
