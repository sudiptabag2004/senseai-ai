if [[ $ENV_TYPE == "production" ]] || [[ $ENV_TYPE == "staging" ]]; then
    SITE_PACKAGES_DIR=/usr/local/lib/python3.8/
else
    SITE_PACKAGES_DIR=./venv/lib/python3.10
fi

SITE_PACKAGES_DIR=/usr/local/lib/python3.8/
# echo "$SITE_PACKAGES_DIR/site-packages/langchain/chat_models/base.py"

cp langchain/chat_generation.py "$SITE_PACKAGES_DIR/site-packages/langchain_core/outputs/chat_generation.py"
cp langchain/cache.py  "$SITE_PACKAGES_DIR/site-packages/langchain/cache.py"
cp langchain/chat_models.py  "$SITE_PACKAGES_DIR/site-packages/langchain_core/language_models/chat_models.py"
