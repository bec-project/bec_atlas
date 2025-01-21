import pytest
from bec_lib import messages

from bec_atlas.ingestor.data_ingestor import DataIngestor


@pytest.fixture
def scan_ingestor(backend):
    client, app = backend
    app.redis_websocket.users = {}
    ingestor = DataIngestor(config=app.config)
    yield ingestor
    ingestor.shutdown()


# @pytest.mark.timeout(60)
# def test_scan_ingestor_create_scan(scan_ingestor, backend):
#     """
#     Test that the login endpoint returns a token.
#     """
#     client, app = backend
#     msg = messages.ScanStatusMessage(
#         metadata={},
#         scan_id="92429a81-4bd4-41c2-82df-eccfaddf3d96",
#         status="open",
#         # session_id="5cc67967-744d-4115-a46b-13246580cb3f",
#         info={
#             "readout_priority": {
#                 "monitored": ["bpm3i", "diode", "ftp", "bpm5c", "bpm3x", "bpm3z", "bpm4x"],
#                 "baseline": ["ddg1a", "bs1y", "mobdco"],
#                 "async": ["eiger", "monitor_async", "waveform"],
#                 "continuous": [],
#                 "on_request": ["flyer_sim"],
#             },
#             "file_suffix": None,
#             "file_directory": None,
#             "user_metadata": {"sample_name": "testA"},
#             "RID": "5cc67967-744d-4115-a46b-13246580cb3f",
#             "scan_id": "92429a81-4bd4-41c2-82df-eccfaddf3d96",
#             "queue_id": "7d77d976-bee0-4bb8-aabb-2b862b4506ec",
#             "session_id": "5cc67967-744d-4115-a46b-13246580cb3f",
#             "scan_motors": ["samx"],
#             "num_points": 10,
#             "positions": [
#                 [-5.0024118137239455],
#                 [-3.8913007026128343],
#                 [-2.780189591501723],
#                 [-1.6690784803906122],
#                 [-0.557967369279501],
#                 [0.5531437418316097],
#                 [1.6642548529427212],
#                 [2.775365964053833],
#                 [3.886477075164944],
#                 [4.9975881862760545],
#             ],
#             "scan_name": "line_scan",
#             "scan_type": "step",
#             "scan_number": 2,
#             "dataset_number": 2,
#             "exp_time": 0,
#             "frames_per_trigger": 1,
#             "settling_time": 0,
#             "readout_time": 0,
#             "acquisition_config": {"default": {"exp_time": 0, "readout_time": 0}},
#             "scan_report_devices": ["samx"],
#             "monitor_sync": "bec",
#             "scan_msgs": [
#                 "metadata={'file_suffix': None, 'file_directory': None, 'user_metadata': {'sample_name': 'testA'}, 'RID': '5cc67967-744d-4115-a46b-13246580cb3f'} scan_type='line_scan' parameter={'args': {'samx': [-5, 5]}, 'kwargs': {'steps': 10, 'exp_time': 0, 'relative': True, 'system_config': {'file_suffix': None, 'file_directory': None}}} queue='primary'"
#             ],
#             "args": {"samx": [-5, 5]},
#             "kwargs": {
#                 "steps": 10,
#                 "exp_time": 0,
#                 "relative": True,
#                 "system_config": {"file_suffix": None, "file_directory": None},
#             },
#         },
#         timestamp=1732610545.15924,
#     )
#     scan_ingestor.update_scan_status(msg, deployment_id="678aa8d4875568640bd92174")

#     response = client.post(
#         "/api/v1/user/login", json={"username": "admin@bec_atlas.ch", "password": "admin"}
#     )
#     client.headers.update({"Authorization": f"Bearer {response.json()}"})

#     session_id = msg.info.get("session_id")
#     scan_id = msg.scan_id
#     response = client.get("/api/v1/scans/session", params={"session_id": session_id})
#     assert response.status_code == 200
#     out = response.json()[0]
#     # assert out["session_id"] == session_id
#     assert out["scan_id"] == scan_id
#     assert out["status"] == "open"

#     msg.status = "closed"
#     scan_ingestor.update_scan_status(msg, deployment_id="678aa8d4875568640bd92174")
#     response = client.get("/api/v1/scans/id", params={"scan_id": scan_id})
#     assert response.status_code == 200
#     out = response.json()
#     assert out["status"] == "closed"
#     assert out["scan_id"] == scan_id

#     response = client.get("/api/v1/scans/session", params={"session_id": session_id})
#     assert response.status_code == 200
#     out = response.json()
#     assert len(out) == 1
