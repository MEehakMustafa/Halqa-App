from fastapi import Query


class PageParams:
    """Shared pagination query params: ?page=1&limit=20 on every list endpoint."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number"),
        limit: int = Query(20, ge=1, le=100, description="items per page"),
    ):
        self.limit = limit
        self.offset = (page - 1) * limit


def paginate(query, params: PageParams):
    return query.offset(params.offset).limit(params.limit).all()
