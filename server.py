import argparse
import asyncio
import logging
import os

from aiohttp import web
import aiofiles

CHUNK_SIZE = 256 * 1024

logger = logging.getLogger(__name__)


async def archive(request):
    archive_hash = request.match_info['archive_hash']

    requested_photos_directory_path = os.path.join(
        request.app['photo_general_directory_path'],
        archive_hash
    )
    if not os.path.exists(requested_photos_directory_path):
        raise web.HTTPNotFound(reason='Архив не существует или был удален')

    zip_process = await asyncio.create_subprocess_exec(
        'zip',
        '-r',
        '-',
        '.',
        cwd=requested_photos_directory_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    response = web.StreamResponse()
    response.enable_chunked_encoding()
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'
    await response.prepare(request)

    while True:
        try:
            data_chunk = await zip_process.stdout.read(CHUNK_SIZE)
            logger.debug('Sending archive chunk ...')
            await response.write(data_chunk)
            if request.app['delay']:
                await asyncio.sleep(request.app['delay'])
            if not data_chunk:
                break
        except asyncio.CancelledError:
            logger.warning('Download was interrupted')
            zip_process.kill()
            logger.warning('Zip process was killed')
            await zip_process.communicate()
            raise
        finally:
            response.force_close()

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Microservice for downloading archived photos'
    )
    parser.add_argument('-l', '--logging', action='store_true', default=False,
                        help='logging')
    parser.add_argument('-d', '--delay', type=int, default=0,
                        help='delay between chunks of zip archive')
    parser.add_argument('-p', '--path', default='test_photos',
                        help='photos general directory path')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    )
    logger.disabled = not args.logging

    app = web.Application()
    app['delay'] = args.delay
    app['photo_general_directory_path'] = args.path
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
