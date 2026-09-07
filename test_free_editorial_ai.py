import json
import unittest

from free_editorial_ai import API_URL, free_model_name, generate_editorial_drafts


def valid_draft() -> dict:
    return {
        "headline": "Fuentes públicas delimitan una jornada de continuidad en el corredor",
        "deck": (
            "La selección separa las señales publicadas por los medios del diagnóstico operativo "
            "y conserva visibles los límites que todavía impiden extraer una conclusión más amplia."
        ),
        "situation": [
            "La jornada reúne referencias sobre navegación y actividad portuaria que deben leerse como afirmaciones atribuidas. Reuters describe el foco informativo, mientras el monitor mantiene su diagnóstico dentro de los datos observados y evita convertir una noticia aislada en una medición completa del corredor.",
            "La comparación útil está en las coincidencias y en los vacíos. Las fuentes seleccionadas hablan de asuntos relacionados, pero no ofrecen por sí solas una serie homogénea de tráfico, una ventana temporal común ni una confirmación suficiente para modificar la clasificación operativa vigente.",
        ],
        "sections": [
            {
                "title": "Tráfico",
                "paragraph": (
                    "Reuters concentra su referencia en el tráfico, aunque el titular disponible no permite reconstruir "
                    "volúmenes, rutas ni periodos comparables. La señal sirve para orientar la comprobación, pero debe "
                    "contrastarse con avisos oficiales y datos operativos antes de presentarla como un cambio sostenido."
                ),
            }
        ],
        "meaning": [
            "La combinación apunta a una agenda informativa activa, no a una prueba autónoma de variación material. El valor editorial está en mostrar qué fuente sostiene cada afirmación, qué parte coincide con el monitor y qué dato adicional sería necesario para confirmar una tendencia con alcance regional.",
        ],
        "watch": [
            "Comprobar nuevos avisos oficiales sobre navegación y servicios portuarios.",
            "Contrastar cualquier cambio de tono con una medición operativa independiente.",
            "Distinguir una novedad puntual de una tendencia mantenida en varias ediciones.",
        ],
    }


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


class FreeEditorialAITests(unittest.TestCase):
    def setUp(self):
        self.fallback = valid_draft()
        self.facts = {"monitor": {"status": "continuidad"}, "selected_sources": [{"source": "Reuters"}]}
        self.sources = {"es": {"Tráfico": ["Reuters"]}}

    def call(self, candidate: dict, **overrides):
        captured = {}

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            envelope = {"choices": [{"message": {"content": json.dumps(candidate, ensure_ascii=False)}}]}
            return FakeResponse(envelope)

        result = generate_editorial_drafts(
            site_name="Sitio de prueba",
            site_url="https://example.com",
            facts=self.facts,
            fallbacks={"es": self.fallback},
            sources_by_section=self.sources,
            api_key="clave-de-prueba",
            opener=opener,
            **overrides,
        )
        return result, captured

    def test_paid_model_slug_is_never_accepted(self):
        self.assertEqual(free_model_name("vendor/model-paid"), "openrouter/free")
        self.assertEqual(free_model_name(":free"), "openrouter/free")
        self.assertEqual(free_model_name("vendor/model:free"), "vendor/model:free")

    def test_missing_key_uses_fallback_without_network(self):
        def forbidden_opener(*args, **kwargs):
            raise AssertionError("No debe abrir la red sin clave")

        drafts, engine, status = generate_editorial_drafts(
            site_name="Sitio de prueba",
            site_url="https://example.com",
            facts=self.facts,
            fallbacks={"es": self.fallback},
            sources_by_section=self.sources,
            api_key="",
            opener=forbidden_opener,
        )
        self.assertEqual((engine, status), ("rules", "no-key"))
        self.assertEqual(drafts["es"], self.fallback)
        self.assertIsNot(drafts["es"], self.fallback)

    def test_valid_response_is_used_without_putting_key_in_url(self):
        (drafts, engine, status), captured = self.call({"es": valid_draft()}, model="paid/model")
        self.assertEqual((engine, status), ("openrouter-free", "ok"))
        self.assertEqual(drafts["es"]["sections"][0]["title"], "Tráfico")
        self.assertEqual(captured["request"].full_url, API_URL)
        self.assertNotIn("clave-de-prueba", captured["request"].full_url)
        request_body = json.loads(captured["request"].data.decode("utf-8"))
        self.assertEqual(request_body["model"], "openrouter/free")

    def test_unseen_number_rejects_the_whole_response(self):
        candidate = valid_draft()
        candidate["meaning"][0] += " La muestra incluiría 77 casos."
        (drafts, engine, status), _ = self.call({"es": candidate})
        self.assertEqual((engine, status), ("rules", "validation-es"))
        self.assertEqual(drafts["es"], self.fallback)

    def test_short_source_name_requires_a_real_attribution(self):
        self.sources = {"es": {"Tráfico": ["AP"]}}
        (_, engine, status), _ = self.call({"es": valid_draft()})
        self.assertEqual((engine, status), ("rules", "validation-es"))


if __name__ == "__main__":
    unittest.main()
