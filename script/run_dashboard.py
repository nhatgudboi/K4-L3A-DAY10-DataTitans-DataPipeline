from __future__ import annotations

import logging
from core.config import load_settings
from observability.dashboard import generate_interactive_dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    settings = load_settings()
    out_path = settings.paths.project_dir / "data" / "reports" / "observability_dashboard.html"
    dashboard_file = generate_interactive_dashboard(settings, out_path)
    logger.info("🎉 Interactive Observability Dashboard generated successfully at:")
    logger.info("   file:///%s", dashboard_file.resolve().as_posix())


if __name__ == "__main__":
    main()
