class Deployment:
    def __init__(self, id: str, sha256: str) -> None:
        self.id = id
        self.sha256 = sha256


class Runtime:
    def __init__(self, id: str, sha256: str) -> None:
        self.id = id
        self.sha256 = sha256


class Status:
    def __init__(
        self,
        runtime: Runtime,
        deployment: Deployment | None,
    ) -> None:
        self.runtime = runtime
        self.deployment = deployment
