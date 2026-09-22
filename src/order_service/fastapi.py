from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Order Service")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
