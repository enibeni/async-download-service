from aiohttp import web


async def handle_404(request):
    response = web.Response(text="Архив не существует или был удален", status=404)
    return response


def create_error_middleware(overrides):

    @web.middleware
    async def error_middleware(request, handler):
        try:
            return await handler(request)
        except web.HTTPException as ex:
            override = overrides.get(ex.status)
            if override:
                return await override(request)

            raise
        except Exception:
            request.protocol.logger.exception("Error handling request")
            return await overrides[500](request)

    return error_middleware


def setup_middlewares(app):
    error_middleware = create_error_middleware({
        404: handle_404,
    })
    app.middlewares.append(error_middleware)