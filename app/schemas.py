"""The base every request model shares.

`extra="forbid"` is the load-bearing part: an unknown field is a 422 before any model is called, so
a browser cannot smuggle in a `model`, a system prompt or an unlisted option. Each feature's own
request models live beside that feature's routes.
"""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
