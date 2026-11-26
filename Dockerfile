FROM ollama/ollama:latest
RUN apt-get update && apt-get install -y python3 python3-pip util-linux procps && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages requests pandas matplotlib numpy || pip3 install requests pandas matplotlib numpy
WORKDIR /work
COPY pidlab ./pidlab
COPY sandbox_run.sh .
ENV CUDA_VISIBLE_DEVICES=-1 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_HOST=127.0.0.1:11434
ENTRYPOINT []
