Optional verified package cache for restricted/offline Docker builds. Populate with:

    python -m pip download --only-binary=:all: -r requirements.txt -d wheelhouse
    docker build --build-arg PIP_NO_INDEX=1 -t sportsml-lab .

Generated wheels are ignored by Git; never disable TLS or package verification.
