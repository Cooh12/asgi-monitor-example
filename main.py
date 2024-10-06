import asyncio
import logging
import random

from aiohttp.web import run_app, Application, HTTPInternalServerError, HTTPNotFound, json_response, Response
from asgi_monitor.integrations.aiohttp import TracingConfig, setup_tracing
from asgi_monitor.logging import configure_logging
from asgi_monitor.logging.aiohttp import TraceAccessLogger
from asgi_monitor.tracing import span


from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

APP_NAME = "aiohttp-example"
GRPC_ENDPOINT = "http://jaeger:4317"


async def get_500_error(request) -> None:
    raise HTTPInternalServerError(text="Internal Server Error")




async def hello(request):
    return Response(text="Hello, world")


async def get_1000ms(request):
    with tracer.start_as_current_span("sleep 0.1"):
        await asyncio.sleep(0.1)
        logger.error("sick")
    with tracer.start_as_current_span("sleep 0.2"):
        await asyncio.sleep(0.2)
        logger.error("still sick")
    with tracer.start_as_current_span("sleep 0.3"):
        await asyncio.sleep(0.3)
        logger.warning("normal")
    with tracer.start_as_current_span("sleep 0.4"):
        await asyncio.sleep(0.4)
        logger.info("full energy")
    return json_response({"message": "ok", "status": "success"})

@span
def nested_func() -> int:
    num = random.randint(1, 10)
    current_span = trace.get_current_span()
    current_span.set_attribute("num", num)
    current_span.add_event("num rendered")
    return num

async def get_span(request):
    num = nested_func()
    return json_response({"message": "ok", "status": "success", "num": num})


async def get_404(request) -> None:
    logger.error("Not Found", extra={"status_code": 404})
    raise HTTPNotFound(text="Not Found")

async def get_infinity() -> float:
    return 1 / 0


def setup_routes(app: Application) -> None:
    app.router.add_get("/slow/1000ms", get_1000ms)
    app.router.add_get("/slow/span", get_span)
    app.router.add_get("/get_404", get_404)
    app.router.add_get("/get_infinity", get_infinity)
    app.router.add_get("/", hello)
    app.router.add_get("/error", get_500_error)


def main() -> None:
    configure_logging(json_format=True, include_trace=True)

    resource = Resource.create(
        attributes={
            "service.name": APP_NAME,
            "compose_service": APP_NAME,
        },
    )
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(GRPC_ENDPOINT)))

    trace_config = TracingConfig(tracer_provider=tracer_provider)

    app = Application()

    setup_tracing(app=app, config=trace_config)

    setup_routes(app)

    try:
        run_app(app, access_log=logger, access_log_class=TraceAccessLogger)
    finally:
        logger.info("Stopped")


if __name__ == "__main__":
    main()