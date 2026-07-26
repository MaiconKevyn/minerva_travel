"""O perfil reutilizável da família: guardar uma vez, carregar em cada guia."""

from fastapi.testclient import TestClient

from minerva_travel import storage
from minerva_travel.app import app
from minerva_travel.auth import AuthenticatedUser, get_current_user
from minerva_travel.contract_limits import MAX_GUIDE_CHILD_AGE, MIN_GUIDE_YEAR
from minerva_travel.persistence import GuideRepository, purge_all_data_for_owner


def _profile_payload(**overrides):
    payload = {
        "family_name": "Família Lima",
        "parents": [{"id": "p1", "name": "Marina"}],
        "children": [{"id": "c1", "name": "Aurora", "birth_year": 2018}],
    }
    payload.update(overrides)
    return payload


def test_repository_replaces_the_whole_profile_and_scopes_it_by_owner(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")

    created = repository.save_family_profile(
        user_id="user-a",
        family_name="Família Lima",
        parents=[{"id": "p1", "name": "Marina"}],
        children=[{"id": "c1", "name": "Aurora", "birth_year": 2018}],
        expected_revision=None,
    )

    assert created is not None
    assert created.revision == 1
    assert repository.family_profile_for_owner("user-b") is None

    replaced = repository.save_family_profile(
        user_id="user-a",
        family_name="Família Lima",
        parents=[{"id": "p1", "name": "Marina"}, {"id": "p2", "name": "Rui"}],
        children=[{"id": "c2", "name": "Bento", "birth_year": 2020}],
        expected_revision=1,
    )

    # Substituição do bloco inteiro: a criança anterior sai, não convive com a nova.
    assert replaced is not None
    assert replaced.revision == 2
    assert [child["name"] for child in replaced.children] == ["Bento"]
    assert len(replaced.parents) == 2


def test_repository_refuses_a_stale_write_instead_of_overwriting_it(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    repository.save_family_profile(
        user_id="user-a",
        family_name="Família Lima",
        parents=[{"id": "p1", "name": "Marina"}],
        children=[{"id": "c1", "name": "Aurora", "birth_year": 2018}],
        expected_revision=None,
    )

    # A outra aba ainda acha que não existe perfil nenhum.
    assert (
        repository.save_family_profile(
            user_id="user-a",
            family_name="Outra família",
            parents=[{"id": "p9", "name": "Alguém"}],
            children=[{"id": "c9", "name": "Outra", "birth_year": 2019}],
            expected_revision=None,
        )
        is None
    )
    stored = repository.family_profile_for_owner("user-a")
    assert stored is not None
    assert stored.family_name == "Família Lima"
    assert stored.revision == 1


def test_deleting_the_profile_is_idempotent_and_keeps_the_drafts(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    draft = repository.create_draft(user_id="user-a", title="Paris", payload={"step": 1})
    repository.save_family_profile(
        user_id="user-a",
        family_name="Família Lima",
        parents=[{"id": "p1", "name": "Marina"}],
        children=[{"id": "c1", "name": "Aurora", "birth_year": 2018}],
        expected_revision=None,
    )

    assert repository.delete_family_profile("user-a") is True
    assert repository.delete_family_profile("user-a") is False
    assert repository.family_profile_for_owner("user-a") is None
    # Apagar os dados guardados não pode levar junto o guia em andamento.
    assert repository.get_draft_for_owner(draft.id, "user-a") is not None


def test_account_deletion_purges_the_family_profile(tmp_path):
    repository = GuideRepository(tmp_path / "minerva.sqlite3")
    repository.save_family_profile(
        user_id="user-a",
        family_name="Família Lima",
        parents=[{"id": "p1", "name": "Marina"}],
        children=[{"id": "c1", "name": "Aurora", "birth_year": 2018}],
        expected_revision=None,
    )
    repository.save_family_profile(
        user_id="user-b",
        family_name="Família Souza",
        parents=[{"id": "p1", "name": "Ana"}],
        children=[{"id": "c1", "name": "Théo", "birth_year": 2017}],
        expected_revision=None,
    )

    purge_all_data_for_owner(repository, "user-a")

    assert repository.family_profile_for_owner("user-a") is None
    assert repository.family_profile_for_owner("user-b") is not None


def _client_for(user_id: str) -> TestClient:
    async def current_user():
        return AuthenticatedUser(id=user_id)

    app.dependency_overrides[get_current_user] = current_user
    return TestClient(app)


def test_profile_api_saves_reloads_and_never_caches_child_names(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")

    try:
        client = _client_for("user-a")
        empty = client.get("/api/family-profile")
        saved = client.put("/api/family-profile", json=_profile_payload())
        loaded = client.get("/api/family-profile")
        updated = client.put(
            "/api/family-profile",
            json=_profile_payload(family_name="Família Lima e Souza", revision=1),
        )
        stale = client.put("/api/family-profile", json=_profile_payload(revision=1))
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert empty.json() == {"profile": None}
    assert saved.status_code == 200
    assert saved.json()["revision"] == 1
    assert loaded.json()["profile"]["children"][0] == {
        "id": "c1",
        "name": "Aurora",
        "birth_year": 2018,
    }
    # Nome de criança não fica em cache de navegador nem de proxy.
    assert loaded.headers["cache-control"] == "private, no-store, max-age=0"
    assert updated.json()["family_name"] == "Família Lima e Souza"
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "family_profile_revision_conflict"


def test_one_account_never_reads_or_overwrites_another_family(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")

    try:
        _client_for("user-a").put("/api/family-profile", json=_profile_payload())
        client_b = _client_for("user-b")
        seen_by_b = client_b.get("/api/family-profile")
        # A revisão da outra conta não serve de chave para escrever na dela.
        written_by_b = client_b.put(
            "/api/family-profile",
            json=_profile_payload(family_name="Família Souza", revision=1),
        )
        client_b.delete("/api/family-profile")
        surviving = _client_for("user-a").get("/api/family-profile")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert seen_by_b.json() == {"profile": None}
    assert written_by_b.status_code == 409
    assert surviving.json()["profile"]["family_name"] == "Família Lima"


def test_profile_api_refuses_payloads_the_guide_could_not_use(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")
    # Um ano de nascimento que sai da faixa de idade aceita pelo guia viraria
    # 422 só na geração, depois de a família ter preenchido tudo de novo.
    too_old = MIN_GUIDE_YEAR - MAX_GUIDE_CHILD_AGE - 1

    try:
        client = _client_for("user-a")
        rejected = [
            client.put("/api/family-profile", json=_profile_payload(children=[])),
            client.put("/api/family-profile", json=_profile_payload(parents=[])),
            client.put("/api/family-profile", json=_profile_payload(family_name="")),
            client.put(
                "/api/family-profile",
                json=_profile_payload(
                    children=[{"id": "c1", "name": "Aurora", "birth_year": too_old}]
                ),
            ),
            client.put(
                "/api/family-profile",
                json=_profile_payload(
                    parents=[{"id": "same", "name": "Marina"}],
                    children=[{"id": "same", "name": "Aurora", "birth_year": 2018}],
                ),
            ),
            client.put(
                "/api/family-profile",
                json=_profile_payload(photo_url="https://exemplo.test/foto.jpg"),
            ),
        ]
        stored = client.get("/api/family-profile")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert [response.status_code for response in rejected] == [422] * 6
    assert stored.json() == {"profile": None}


def test_a_validator_message_reaches_the_user_instead_of_a_server_error(tmp_path, monkeypatch):
    """O 422 de identificadores repetidos respondia 500 antes desta correção.

    O Pydantic guarda a exceção crua do validador em ``ctx``; o encoder não
    sabia serializá-la e a resposta virava "erro no servidor", sem dizer qual
    campo estava errado.
    """
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")

    try:
        response = _client_for("user-a").put(
            "/api/family-profile",
            json=_profile_payload(
                parents=[{"id": "mesmo", "name": "Marina"}],
                children=[{"id": "mesmo", "name": "Aurora", "birth_year": 2018}],
            ),
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "input_validation_error"
    assert "identificador" in str(body["detail"])


def test_account_export_carries_the_profile_and_no_photo(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path / "runtime")

    try:
        client = _client_for("user-a")
        client.put("/api/family-profile", json=_profile_payload())
        exported = client.get("/api/account/export").json()
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    profile = exported["family_profile"]
    assert profile["family_name"] == "Família Lima"
    assert profile["children"][0]["birth_year"] == 2018
    # Nenhum caminho de foto, consentimento ou roteiro entra no perfil salvo.
    assert set(profile) == {
        "family_name",
        "parents",
        "children",
        "revision",
        "created_at",
        "updated_at",
    }
