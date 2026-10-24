import uvicorn
import sys

from server.nacos_utils import DocParseConfig

if __name__ == '__main__':
    server_config = DocParseConfig().config['server']
    uvicorn.run(
        'server.controller:app',
        host=server_config['host'],
        port=server_config['port'],
        workers=server_config.get('workers', None)
    )
