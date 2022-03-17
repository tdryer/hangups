"""Example of using hangups to get information about your account."""

import asyncio

import hangups

from common import run_example


async def get_self_info(client, _):
    request = hangups.hangouts_pb2.GetSelfInfoRequest(
        request_header=client.get_request_header(),
    )
    res = await client.get_self_info(request)
    print(res)


if __name__ == "__main__":
    run_example(get_self_info)
