# 1. Base Image: 파이썬 3.12 (가벼운 slim 버전)
FROM python:3.12-slim

# 2. 시스템 패키지 설치 (git, PostgreSQL 연동 등에 필요)
RUN apt-get update && apt-get install -y \
    git \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 3. uv 설치 (가장 최신 방법)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 4. 작업 디렉토리 설정
WORKDIR /app

# 5. 의존성 파일 복사 (캐시 효율을 위해 코드보다 먼저 복사)
COPY pyproject.toml uv.lock ./

# 6. 라이브러리 설치 (가상환경 .venv를 컨테이너 안에 생성)
# --frozen: 락파일(uv.lock) 기준으로 엄격하게 설치
RUN uv sync --frozen --no-cache

# 7. 프로젝트 코드 전체 복사
COPY . .

# 8. 환경 변수 설정 (중요: 가상환경 경로를 PATH에 추가)
# 이러면 'uv run' 안 붙이고 그냥 'python'이나 'gunicorn' 해도 됨!
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 9. 포트 노출 (문서용)
EXPOSE 8000

# 10. 실행 명령어 (기본값)
# Gunicorn으로 실행 (config는 settings.py가 있는 폴더 이름)
CMD ["/app/.venv/bin/gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]