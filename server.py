import asyncio

from aiohttp import web
import aiofiles
import os

CHUNK_SIZE = 256 * 1024
PHOTOS_GENERAL_DIRECTORY_PATH = 'test_photos'


async def archive(request):
    archive_hash = request.match_info['archive_hash']

    requested_photos_directory_path = os.path.join(
        PHOTOS_GENERAL_DIRECTORY_PATH,
        archive_hash
    )
    if not os.path.exists(requested_photos_directory_path):
        raise web.HTTPNotFound(reason='Архив не существует или был удален')

    process = await asyncio.create_subprocess_exec(
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
        data_chunk = await process.stdout.read(CHUNK_SIZE)
        await response.write(data_chunk)
        if not data_chunk:
            break

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
