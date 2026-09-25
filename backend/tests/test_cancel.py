"""Cancel: if the browser stops waiting, the finished analysis is not saved."""

import asyncio

import pytest

from config import get_settings
from models import Analysis
from routers.analyses import Cancelled, analyze_and_save


class FakeRequest:
    def __init__(self, disconnected):
        self.disconnected = disconnected

    async def is_disconnected(self):
        return self.disconnected


def run(session, request):
    return asyncio.run(
        analyze_and_save(
            session,
            get_settings(),
            None,
            None,
            resume_filename="cv.txt",
            resume_text="Python developer",
            jd_text="Need Python",
            jd_source="paste",
            jd_filename=None,
            request=request,
        )
    )


def test_cancelled_analysis_is_not_saved(make_client):
    with make_client() as client:
        session = client.app.state.session_factory()
        with pytest.raises(Cancelled):
            run(session, FakeRequest(disconnected=True))
        assert session.query(Analysis).count() == 0
        session.close()


def test_analysis_is_saved_while_the_browser_waits(make_client):
    with make_client() as client:
        session = client.app.state.session_factory()
        row = run(session, FakeRequest(disconnected=False))
        assert row.id and session.query(Analysis).count() == 1
        session.close()
