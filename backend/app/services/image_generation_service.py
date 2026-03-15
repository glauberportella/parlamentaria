"""Image generation service using Playwright + Jinja2 HTML→PNG."""

import os
import uuid

from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)

# Optimal dimensions per social network
SOCIAL_DIMENSIONS: dict[str, tuple[int, int]] = {
    "twitter": (1200, 675),
    "facebook": (1200, 630),
    "instagram": (1080, 1080),
    "linkedin": (1200, 627),
    "discord": (1200, 675),
    "reddit": (1200, 675),
}


class ImageGenerationService:
    """Generates infographic cards for social media posts.

    Renders HTML/CSS templates via Playwright (headless Chromium)
    and exports as PNG. Ensures pixel-perfect text and consistent
    branding across all images.
    """

    def __init__(self, templates_dir: str | None = None):
        base = templates_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "templates", "social"
        )
        self.jinja_env = Environment(
            loader=FileSystemLoader(base),
            autoescape=True,
        )
        self._playwright = None
        self._browser = None

    async def _get_browser(self):
        """Reuse browser instance (connection pool)."""
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch()
        return self._browser

    async def _render_template(
        self,
        template_name: str,
        context: dict,
        width: int,
        height: int,
        output_path: str,
    ) -> str:
        """Render a Jinja2 HTML template as PNG via Playwright.

        Args:
            template_name: Template file name (e.g. 'comparativo.html').
            context: Data to inject into the template.
            width: Viewport width in pixels.
            height: Viewport height in pixels.
            output_path: Output PNG file path.

        Returns:
            Absolute path to the generated PNG file.
        """
        template = self.jinja_env.get_template(template_name)
        html = template.render(**context)

        browser = await self._get_browser()
        page = await browser.new_page(viewport={"width": width, "height": height})
        await page.set_content(html, wait_until="networkidle")
        await page.screenshot(path=output_path, type="png")
        await page.close()
        return output_path

    def _dimensions_for(self, rede: str) -> tuple[int, int]:
        return SOCIAL_DIMENSIONS.get(rede, SOCIAL_DIMENSIONS["twitter"])

    def _output_path(self, tipo: str, rede: str) -> str:
        os.makedirs(settings.social_images_dir, exist_ok=True)
        filename = f"{tipo}_{rede}_{uuid.uuid4().hex[:8]}.png"
        return os.path.join(settings.social_images_dir, filename)

    async def generate_comparativo_image(
        self,
        proposicao: str,
        voto_popular_sim: float,
        voto_popular_nao: float,
        resultado_camara: str,
        alinhamento: float,
        rede: str = "twitter",
    ) -> str:
        """Generate a Povo vs Câmara comparative image."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "comparativo.html",
            {
                "proposicao": proposicao,
                "sim": voto_popular_sim,
                "nao": voto_popular_nao,
                "resultado": resultado_camara,
                "alinhamento": alinhamento,
            },
            width,
            height,
            self._output_path("comparativo", rede),
        )

    async def generate_resumo_semanal_image(
        self,
        total_proposicoes: int,
        total_votos: int,
        total_eleitores: int,
        top_proposicoes: list[dict],
        periodo: str,
        rede: str = "twitter",
    ) -> str:
        """Generate a weekly summary card."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "resumo_semanal.html",
            {
                "total_proposicoes": total_proposicoes,
                "total_votos": total_votos,
                "total_eleitores": total_eleitores,
                "top": top_proposicoes[:5],
                "periodo": periodo,
            },
            width,
            height,
            self._output_path("resumo_semanal", rede),
        )

    async def generate_votacao_image(
        self,
        proposicao: str,
        sim_pct: float,
        nao_pct: float,
        abstencao_pct: float,
        total_votos: int,
        temas: list[str],
        rede: str = "twitter",
    ) -> str:
        """Generate a voting results bar chart image."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "votacao.html",
            {
                "proposicao": proposicao,
                "sim": sim_pct,
                "nao": nao_pct,
                "abstencao": abstencao_pct,
                "total": total_votos,
                "temas": temas,
            },
            width,
            height,
            self._output_path("votacao", rede),
        )

    async def generate_destaque_proposicao_image(
        self,
        proposicao: str,
        ementa_resumida: str,
        areas: list[str],
        sim_pct: float,
        nao_pct: float,
        rede: str = "twitter",
    ) -> str:
        """Generate a featured proposition highlight card."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "destaque.html",
            {
                "proposicao": proposicao,
                "ementa": ementa_resumida,
                "areas": areas,
                "sim": sim_pct,
                "nao": nao_pct,
            },
            width,
            height,
            self._output_path("destaque", rede),
        )

    async def generate_explicativo_image(
        self,
        proposicao: str,
        o_que_muda: str,
        areas: list[str],
        argumentos_favor: list[str],
        argumentos_contra: list[str],
        rede: str = "twitter",
    ) -> str:
        """Generate an educational explainer card."""
        width, height = self._dimensions_for(rede)
        return await self._render_template(
            "explicativo.html",
            {
                "proposicao": proposicao,
                "o_que_muda": o_que_muda,
                "areas": areas,
                "favor": argumentos_favor[:3],
                "contra": argumentos_contra[:3],
            },
            width,
            height,
            self._output_path("explicativo", rede),
        )

    async def close(self) -> None:
        """Close the browser. Call on application shutdown."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
