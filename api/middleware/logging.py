# api/middleware/logging.py
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import uuid


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        # 记录请求信息
        logger.info(f"Request {request_id} started: {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # 记录响应信息
            process_time = time.time() - start_time
            status_code = response.status_code

            logger.info(
                f"Request {request_id} completed: {request.method} {request.url.path} "
                f"- Status: {status_code} - Duration: {process_time:.4f}s"
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request {request_id} failed: {request.method} {request.url.path} "
                f"- Error: {str(e)} - Duration: {process_time:.4f}s"
            )
            raise