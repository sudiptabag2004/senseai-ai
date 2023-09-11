if [[ $ENV_TYPE == "production" ]] || [[ $ENV_TYPE == "staging" ]]; then
    SITE_PACKAGES_DIR=/usr/local/lib/python3.8/
else
    SITE_PACKAGES_DIR=./venv/lib/python3.10
fi

# echo "$SITE_PACKAGES_DIR/site-packages/langchain/chat_models/base.py"

cp langchain/base.py "$SITE_PACKAGES_DIR/site-packages/langchain/chat_models/base.py"
cp langchain/cache.py  "$SITE_PACKAGES_DIR/site-packages/langchain/cache.py"
cp langchain/output.py  "$SITE_PACKAGES_DIR/site-packages/langchain/schema/output.py"
