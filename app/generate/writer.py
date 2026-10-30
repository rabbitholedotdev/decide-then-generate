from __future__ import annotations

from typing import Protocol

from app.catalog import default_catalog
from app.generate.prompt import PromptBundle
from app.models_loader import task_model
from app.settings import Settings, get_settings
from app.types import Decision, Language, SpeechAct


class Writer(Protocol):
    name: str

    async def write(self, bundle: PromptBundle, decision: Decision) -> str:
        ...


class TemplateWriter:
    """Deterministic stand-in so the demo and tests run without an API key.

    Still a writer: it never changes the Decision.
    """

    name = "template"

    def __init__(self, catalog=None):
        self.catalog = catalog or default_catalog()

    async def write(self, bundle: PromptBundle, decision: Decision) -> str:
        del bundle
        names = []
        for pid in decision.product_ids:
            item = self.catalog.get(pid)
            if item:
                names.append(f"{item.name} ({item.price_label})")
        named = ", ".join(names)
        pt = decision.language is Language.PT_BR
        act = decision.speech_act

        if act is SpeechAct.HANDOFF:
            return (
                "Entendi. Vou chamar alguém do balcão para continuar com você. "
                "Não vou seguir com venda por aqui."
                if pt
                else "Understood. I am handing you to a person at the counter. I will not keep selling here."
            )
        if act is SpeechAct.GREET:
            return (
                "Olá, bem-vindo ao Orvalho Atelier. O que você procura hoje — um chá para o dia a dia ou um presente?"
                if pt
                else "Hello, welcome to Orvalho Atelier. What are you looking for today — a daily tea or a gift?"
            )
        if act is SpeechAct.ASK_NEED:
            return (
                "Você busca um chá, um presente ou algum utensílio de preparo?"
                if pt
                else "Are you after a tea, a gift, or brewing gear?"
            )
        if act is SpeechAct.ASK_OCCASION:
            return (
                "Isso é para você ou para presente?"
                if pt
                else "Is this for you or a gift?"
            )
        if act is SpeechAct.ASK_TASTE:
            return (
                "Você prefere verde, preto, oolong ou uma infusão sem cafeína?"
                if pt
                else "Do you lean green, black, oolong, or a caffeine-free infusion?"
            )
        if act is SpeechAct.ASK_CAFFEINE:
            return (
                "Como você quer a cafeína: normal, baixa ou nenhuma?"
                if pt
                else "How do you want caffeine: regular, low, or none?"
            )
        if act is SpeechAct.ASK_BUDGET:
            return (
                "Qual faixa cabe hoje: até 40, até 90, ou podemos olhar utensílios acima disso?"
                if pt
                else "Which band fits today: under 40, under 90, or gear above that?"
            )
        if act is SpeechAct.ASK_EXPERIENCE:
            return (
                "Você já prepara chá em casa ou prefere um kit para começar?"
                if pt
                else "Do you already brew at home, or do you want a starter kit?"
            )
        if act is SpeechAct.EDUCATE:
            return (
                f"Notas de preparo do catálogo para {named or 'o item escolhido'}. Sem alegação de saúde — é só bebida. Quer que eu ajuste a recomendação?"
                if pt
                else f"Catalog brew notes for {named or 'the chosen item'}. No health claims — it is a beverage. Want me to adjust the pick?"
            )
        if act is SpeechAct.COMPARE:
            return (
                f"Comparando só o que está no catálogo: {named or 'dois itens'}. Qual lado te agrada mais?"
                if pt
                else f"Comparing catalog items only: {named or 'two items'}. Which side fits you?"
            )
        if act is SpeechAct.HANDLE_OBJECTION:
            return (
                f"Faz sentido. Uma saída mais leve no catálogo é {named or 'o kit degustação'}. Quer olhar esse caminho?"
                if pt
                else f"Fair. A lighter catalog path is {named or 'the tasting kit'}. Want to look at that?"
            )
        if act is SpeechAct.RECOMMEND:
            return (
                f"Com o que você me contou, eu indicaria {named or 'o kit degustação (3 amostras)'}. Sem fechar nada ainda — isso te atende?"
                if pt
                else f"From what you told me, I would point to {named or 'the tasting kit'}. No purchase step yet — does that fit?"
            )
        if act is SpeechAct.OFFER:
            return (
                f"Posso separar {named or 'o item combinado'} no balcão para você levar hoje. Quer que eu faça essa reserva?"
                if pt
                else f"I can hold {named or 'the agreed item'} at the counter for you today. Shall I place that hold?"
            )
        if act is SpeechAct.CONFIRM:
            return (
                f"Confirmado: {named or 'o item combinado'}. O balcão separa; pagamento é lá, não neste chat."
                if pt
                else f"Confirmed: {named or 'the agreed item'}. The counter will hold it; payment happens there, not in this chat."
            )
        if act is SpeechAct.CLOSE:
            return (
                "Quando quiser voltar ao balcão, é só chamar. Bom chá."
                if pt
                else "Whenever you want the counter again, just call. Enjoy the tea."
            )
        return "Posso te ajudar a escolher pelo catálogo." if pt else "I can help you choose from the catalog."


class OpenAIWriter:
    name = "openai"

    def __init__(self, client=None):
        self._client = client

    async def write(self, bundle: PromptBundle, decision: Decision) -> str:
        from app.openai_client import get_async_openai

        del decision
        spec = task_model("generate")
        client = self._client or get_async_openai()
        response = await client.chat.completions.create(
            model=spec.model,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            messages=bundle.messages(),
        )
        return (response.choices[0].message.content or "").strip()


class RegeneratingWriter:
    """Wraps a writer and prepends a fix-up instruction for the single retry."""

    def __init__(self, inner: Writer):
        self.inner = inner
        self.name = inner.name

    async def write(self, bundle: PromptBundle, decision: Decision, repair: str | None = None) -> str:
        if not repair:
            return await self.inner.write(bundle, decision)
        repaired = PromptBundle(
            prefix=bundle.prefix,
            layer_retrieve=bundle.layer_retrieve,
            layer_decision=bundle.layer_decision,
            layer_transcript=bundle.layer_transcript
            + "\n\nRepair the previous draft. Violations to fix:\n"
            + repair,
            version=bundle.version,
        )
        return await self.inner.write(repaired, decision)


def build_writer(settings: Settings | None = None, client=None) -> Writer:
    cfg = settings or get_settings()
    if cfg.writer == "openai":
        return OpenAIWriter(client=client)
    return TemplateWriter()
