"""Agente con memoria de corto plazo. Usa create_agent real, herramientas reales e InMemorySaver;
solo el modelo de chat está guionado (no llama a OpenAI)."""

from datetime import timedelta

from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.factory import make_history_trimmer
from app.engine.recommender import recommend
from app.memory.sessions import SessionRegistry
from tests.conftest import tool_call

SID = "6f1c0a3e-8c1a-4c5e-9b1a-2f3e4d5c6b7a"
SID2 = "0b9d3c1e-2f4a-4b6c-8d7e-1a2b3c4d5e6f"
PLOT_ARGS = {"previous_crops": ["papa"], "priorities": ["speed"], "altitude_masl": 2800, "irrigation": "yes"}


def send(client, sid, text):
    return client.post(f"/v1/sessions/{sid}/messages", json={"message": text})


def test_agent_remembers_within_session_and_recommends(make_client, scripted, kb):
    model = scripted(
        tool_call("update_plot", PLOT_ARGS, "c1"), AIMessage(content="¿Cómo es la fertilidad de su suelo?"),
        tool_call("recommend_crop", {}, "c2"), AIMessage(content="Le recomiendo amaranto."),
    )
    c = make_client(model)

    r1 = send(c, SID, "Sembré papa, quiero algo rápido. Estoy a 2800 m con riego.")
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["session_status"] == "new"
    assert b1["reply"] == "¿Cómo es la fertilidad de su suelo?"
    assert b1["plot"]["previous_crops"] == ["papa"] and b1["plot"]["priorities"] == ["speed"]
    assert b1["missing_data"] == ["soil.fertility"]
    assert b1["recommendation"] is None

    r2 = send(c, SID, "No sé, recomiéndeme igual.")
    b2 = r2.json()
    assert b2["session_status"] == "active"
    expected = recommend({"previous_crops": ["papa"], "priorities": ["speed"],
                          "climate": {"altitude_masl": 2800, "irrigation": "yes"}}, kb)
    assert b2["recommendation"]["recommendation"]["crop"] == expected["recommendation"]["crop"]

    # El system prompt del 2.º turno incluye el plot validado (memoria estructurada de la sesión).
    system = model.seen[2][0]
    assert isinstance(system, SystemMessage) and '"previous_crops": ["papa"]' in system.content
    # El modelo vio el turno anterior (memoria de conversación).
    assert any(isinstance(m, HumanMessage) and "Sembré papa" in m.content for m in model.seen[2])


def test_update_plot_reports_validation_errors(make_client, scripted):
    model = scripted(tool_call("update_plot", {"previous_crops": ["papaa"], "priorities": ["speed"]}, "c1"),
                     AIMessage(content="¿Quiso decir papa?"))
    c = make_client(model)
    b = send(c, SID, "Sembré papaa").json()
    tool_msg = next(m for m in model.seen[1] if isinstance(m, ToolMessage))
    assert "UNKNOWN_CROP" in tool_msg.content and "papa" in tool_msg.content
    assert b["plot"] == {"priorities": ["speed"]}  # se guarda lo válido, no lo inválido


def test_recommend_requires_mandatory_data(make_client, scripted):
    model = scripted(tool_call("recommend_crop", {}, "c1"), AIMessage(content="Primero dígame qué sembró."))
    c = make_client(model)
    b = send(c, SID, "¿Qué siembro?").json()
    tool_msg = next(m for m in model.seen[1] if isinstance(m, ToolMessage))
    assert "missing_required" in tool_msg.content
    assert b["recommendation"] is None


def test_search_sources_returns_citations_of_this_turn_only(make_client, scripted):
    model = scripted(tool_call("search_sources", {"query": "gorgojo de los Andes"}, "c1"), AIMessage(content="Según la FAO…"),
                     AIMessage(content="De nada."))
    c = make_client(model)
    first = send(c, SID, "¿Qué es el gorgojo de los Andes?").json()
    assert first["citations"] and any(x["source_id"] == 2 for x in first["citations"])
    second = send(c, SID, "Gracias").json()
    assert second["citations"] == []


def test_sessions_are_isolated(make_client, scripted):
    model = scripted(tool_call("update_plot", PLOT_ARGS, "c1"), AIMessage(content="Anotado."), AIMessage(content="Hola."))
    c = make_client(model)
    send(c, SID, "Sembré papa")
    other = send(c, SID2, "Hola").json()
    assert other["session_status"] == "new" and other["plot"] == {}


def test_delete_forgets_session(make_client, scripted):
    model = scripted(tool_call("update_plot", PLOT_ARGS, "c1"), AIMessage(content="Anotado."), AIMessage(content="Hola de nuevo."))
    c = make_client(model)
    send(c, SID, "Sembré papa")
    assert c.get(f"/v1/sessions/{SID}").json()["plot"]["previous_crops"] == ["papa"]
    assert c.delete(f"/v1/sessions/{SID}").status_code == 204
    assert c.get(f"/v1/sessions/{SID}").status_code == 404
    again = send(c, SID, "Hola").json()
    assert again["session_status"] == "new" and again["plot"] == {}


def test_ttl_expiry_starts_a_new_session(make_client, scripted, clock):
    model = scripted(tool_call("update_plot", PLOT_ARGS, "c1"), AIMessage(content="Anotado."), AIMessage(content="Hola."))
    c = make_client(model)
    send(c, SID, "Sembré papa")
    clock.advance(119)
    assert c.get(f"/v1/sessions/{SID}").status_code == 200
    clock.advance(2)  # 121 min sin actividad
    assert c.get(f"/v1/sessions/{SID}").status_code == 404
    b = send(c, SID, "Hola").json()
    assert b["session_status"] == "new" and b["plot"] == {}
    assert len(model.seen[-1]) == 2  # system + el mensaje nuevo: no quedó nada del hilo anterior


def test_registry_purge_deletes_checkpointer_threads(clock):
    saver = InMemorySaver()
    reg = SessionRegistry(saver, timedelta(minutes=120), clock)
    reg.begin(SID)
    clock.advance(60)
    reg.begin(SID2)
    clock.advance(61)
    assert reg.purge_expired() == [SID]
    assert len(reg) == 1 and reg.is_active(SID2)


def test_history_trimmer_cuts_at_user_turn():
    trim = make_history_trimmer(max_turns=2)
    msgs = [HumanMessage("t1", id="h1"), AIMessage("r1", id="a1"),
            HumanMessage("t2", id="h2"), AIMessage("", id="a2", tool_calls=[{"name": "x", "args": {}, "id": "tc"}]),
            ToolMessage("ok", tool_call_id="tc", id="t2"), AIMessage("r2", id="a2b"),
            HumanMessage("t3", id="h3")]
    out = trim.before_model({"messages": msgs}, None)
    kept = [m.id for m in out["messages"][1:]]
    assert kept == ["h2", "a2", "t2", "a2b", "h3"]  # la llamada a herramienta y su resultado siguen juntos
    assert trim.before_model({"messages": msgs[:4]}, None) is None
