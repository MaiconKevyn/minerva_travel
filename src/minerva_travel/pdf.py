from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from minerva_travel.models import GuideContext

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_guide_html(context: GuideContext, preview: bool = False) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("guide.html")
    css = (TEMPLATE_DIR / "styles.css").read_text(encoding="utf-8")
    return template.render(guide=context, css=css, preview=preview)


def write_pdf(context: GuideContext, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = render_guide_html(context)
    HTML(string=html, base_url=Path.cwd()).write_pdf(output_path)
    return output_path
