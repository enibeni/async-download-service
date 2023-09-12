import argparse
import os
import aiofiles
import asyncio
import logging

from aiohttp import web
from middlewares import create_error_middleware, handle_404


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', type=str, default='photos', help='Set directory with photos')
    parser.add_argument('--debug', type=bool, default=False, help='Set debug mode')
    parser.add_argument('--delay', type=int, default=0, help='Set delay between chunks')
    return parser.parse_args()


async def archive(request):
    archive_hash = request.match_info['archive_hash']
    path = f'{app.photos_path}/{archive_hash}'

    if not os.path.exists(path):
        raise web.HTTPNotFound()

    response = web.StreamResponse()
    response.enable_chunked_encoding()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip'
    await response.prepare(request)

    process = await asyncio.create_subprocess_exec(
        *['zip', '-r', '-', '.'],
        cwd=path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    try:
        while not process.stdout.at_eof():
            chunk = await process.stdout.read(512 * 1000)
            logging.debug(u'Sending archive chunk ...')
            await response.write(chunk)
            await asyncio.sleep(app.delay)

    except asyncio.CancelledError:
        logging.debug('Download was interrupted')
        raise
    except KeyboardInterrupt:
        logging.debug('CTRL+C was pressed. Exiting gracefully...')
        raise
    except SystemExit as e:
        logging.error(f'SystemExit error: {e}')
        raise
    finally:
        if process.returncode is None:
            process.kill()
            await process.communicate()
        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    args = get_args()
    app = web.Application()

    if args.debug or os.getenv('DEBUG') == 'True':
        logging.basicConfig(level=logging.DEBUG)

    app.photos_path = args.path or os.getenv('PHOTOS_PATH', 'photos')
    app.delay = args.delay or float(os.getenv('DELAY', '0'))

    error_middleware = create_error_middleware({
        404: handle_404,
    })
    app.middlewares.append(error_middleware)
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
