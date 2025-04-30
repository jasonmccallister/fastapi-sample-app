from typing import Annotated
import dagger
from dagger import dag, function, object_type, DefaultPath, Service


@object_type
class FastapiSampleApp:
    source: Annotated[dagger.Directory, DefaultPath("/")]

    @function
    async def publish(self) -> str:
        """Publish the application."""
        await self.test()

        return await (
            self.build_env()
            .with_exposed_port(8000)
            .with_entrypoint(args=["fastapi", "dev", "--host=0.0.0.0", "main.py"])
            .publish("ttl.sh/fastapi-sample-app")
        )

    @function
    def run(self) -> Service:
        """Run the application."""

        svc = (
            dag.container()
            .from_("postgres:latest")
            .with_env_variable("POSTGRES_PASSWORD", "secret")
            .with_exposed_port(5432)
            .as_service()
        )

        return (
            self.build_env()
            .with_env_variable("DATABASE_URL", "postgresql://postgres:secret@database/postgres")
            .with_service_binding("database", svc)
            .with_exposed_port(8000)
            .as_service(args=["fastapi", "dev", "--host=0.0.0.0", "main.py"])
        )


    @function
    async def test(self) -> str:
        """Run application tests."""

        svc = (
            dag.container()
            .from_("postgres:latest")
            .with_env_variable("POSTGRES_PASSWORD", "secret")
            .with_exposed_port(5432)
            .as_service()
        )

        versions = ["3.11", "3.10", "3.9"]
        output = ""
        for version in versions:
            output += await (
                self.build_env(version)
                .with_env_variable("DATABASE_URL", "postgresql://postgres:secret@database/postgres")
                .with_service_binding("database", svc)
                .with_exec(["pytest", "-v"]).
                stdout()
            )

        return output

    @function
    def build_env(self, version: str = "3.11") -> dagger.Container:
        """Build the environment for the application."""
        return (
            dag.container()
            .from_(f"python:{version}")
            .with_workdir("/app")
            .with_directory("/app", self.source)
            .with_exec(["pip", "install", "-r", "requirements.txt"])
        )
