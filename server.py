import asyncio
import logging
import os

from aiohttp import web
import aiofiles

CHUNK_SIZE = 256 * 1024
PHOTOS_GENERAL_DIRECTORY_PATH = 'test_photos'
DOWNLOAD_DELAY = 0

logger = logging.getLogger(__name__)


async def archive(request):
    archive_hash = request.match_info['archive_hash']

    requested_photos_directory_path = os.path.join(
        PHOTOS_GENERAL_DIRECTORY_PATH,
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
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'
    await response.prepare(request)

    while True:
        try:
            data_chunk = await zip_process.stdout.read(CHUNK_SIZE)
            logger.debug('Sending archive chunk ...')
            await response.write(data_chunk)
            await asyncio.sleep(DOWNLOAD_DELAY)
            if not data_chunk:
                break
        except asyncio.CancelledError:
            logger.warning('Download was interrupted')
            zip_process.kill()
            logger.warning('Zip process was killed')
            await zip_process.communicate()
            raise
        finally:
            return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    )

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
