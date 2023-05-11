for repo in .libraries/*; do
    cd $repo
    pre-commit run --all-files
    git add -A
    git commit -m "Run pre-commit"
    git push
    cd ..
done
