import os
import aiofiles
import asyncio

from aiohttp import web
from middlewares import create_error_middleware, handle_404


async def archive(request):
    archive_hash = request.match_info['archive_hash']
    path = f'test_photos/{archive_hash}'

    if not os.path.exists(path):
        raise web.HTTPNotFound()

    response = web.StreamResponse()
    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip'
    await response.prepare(request)

    process = await asyncio.create_subprocess_exec(
        *['zip', '-r', '-', '.'],
        cwd=path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    while True:
        line = await process.stdout.read(500)
        await response.write(line)
        if process.stdout.at_eof():
            break

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    error_middleware = create_error_middleware({
        404: handle_404,
    })
    app.middlewares.append(error_middleware)
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
