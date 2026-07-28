import pytest
from helpers import FakeResponse

from media2commons import mediawiki
from media2commons.mediawiki import (
    api_get,
    commons_url_for_sha1,
    login,
    make_session,
    retry_wait,
)

OK = {"query": {"allimages": []}}


@pytest.fixture
def no_sleep(monkeypatch):
    """Record the waits instead of serving them."""
    waits = []
    monkeypatch.setattr(mediawiki.time, "sleep", waits.append)
    return waits


def test_user_agent_names_the_tool_and_a_contact():
    agent = make_session().headers["User-Agent"]
    assert agent.startswith("FuerthWiki-to-Commons-Bot/")
    assert "https://" in agent


def test_retry_after_header_sets_the_wait():
    response = FakeResponse(status=429, headers={"Retry-After": "42"})
    assert retry_wait(response, attempt=0) == 42.0


def test_wait_backs_off_without_a_usable_retry_after():
    # A Retry-After in HTTP-date form is not a number of seconds.
    response = FakeResponse(
        status=429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
    )
    assert retry_wait(response, attempt=0, base=5) == 5
    assert retry_wait(response, attempt=2, base=5) == 20


def test_rate_limited_request_is_retried(fake_session, no_sleep):
    session = fake_session(
        [
            FakeResponse(status=429, headers={"Retry-After": "7"}),
            FakeResponse(OK),
        ]
    )

    assert api_get(session, "https://example.org/api.php", {}) == OK
    assert no_sleep == [7.0]


def test_retries_are_given_up_on(fake_session, no_sleep):
    session = fake_session([FakeResponse(status=429)] * 3)

    with pytest.raises(RuntimeError):
        api_get(session, "https://example.org/api.php", {}, retries=2)

    assert len(no_sleep) == 2


def test_other_errors_are_not_retried(fake_session, no_sleep):
    session = fake_session([FakeResponse(status=404)])

    with pytest.raises(RuntimeError):
        api_get(session, "https://example.org/api.php", {})

    assert no_sleep == []


def allimages(*matches):
    return FakeResponse({"query": {"allimages": list(matches)}})


def test_a_hash_match_yields_its_file_page(fake_session):
    page = "https://commons.wikimedia.org/wiki/File:Rathaus.jpg"
    session = fake_session([allimages({"name": "Rathaus.jpg", "descriptionurl": page})])

    assert commons_url_for_sha1(session, "abc") == page


def test_no_match_yields_an_empty_string(fake_session):
    assert commons_url_for_sha1(fake_session([allimages()]), "abc") == ""


def test_the_file_page_is_built_from_the_name_if_needed(fake_session):
    session = fake_session([allimages({"name": "Rathaus.jpg"})])

    url = commons_url_for_sha1(session, "abc")

    assert url == "https://commons.wikimedia.org/wiki/File:Rathaus.jpg"


def test_a_match_without_anything_to_link_to_is_not_a_url(fake_session):
    assert commons_url_for_sha1(fake_session([allimages({})]), "abc") == ""


def test_the_first_of_several_duplicates_is_used(fake_session):
    session = fake_session(
        [allimages({"name": "First.jpg"}, {"name": "Second.jpg"})]
    )

    assert commons_url_for_sha1(session, "abc").endswith("First.jpg")


def login_responses(result):
    return [
        FakeResponse({"query": {"tokens": {"logintoken": "tok+\\"}}}),
        FakeResponse({"login": result}),
    ]


def test_login_sends_the_token_it_was_given(fake_session):
    session = fake_session(login_responses({"result": "Success", "lgusername": "Bot"}))

    login(session, "Bot", "secret", "https://example.org/api.php")

    post = session.calls[1]
    assert post["method"] == "POST"
    assert post["params"]["lgtoken"] == "tok+\\"
    assert post["params"]["lgname"] == "Bot"


def test_failed_login_raises_with_the_reason(fake_session):
    session = fake_session(
        login_responses({"result": "Failed", "reason": "Incorrect password"})
    )

    with pytest.raises(RuntimeError, match="Incorrect password"):
        login(session, "Bot", "secret", "https://example.org/api.php")


def test_login_without_a_token_raises(fake_session):
    session = fake_session([FakeResponse({"query": {"tokens": {}}})])

    with pytest.raises(RuntimeError, match="login token"):
        login(session, "Bot", "secret", "https://example.org/api.php")
