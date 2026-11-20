"""Skip redundant Pages only after proving this exact commit is already public."""
import os
import subprocess
from canonical_publication import canonical
from canonical_notifications import fetch_public, verify_release


def needed(root, commit, fetcher=fetch_public):
    try:
        verify_release(fetcher, canonical(root), commit)
        return False
    except Exception:
        # A failed or inconsistent probe must never prevent repair publication.
        return True


if __name__ == '__main__':
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    # An explicit manual Pages run remains a way to repair other assets.
    publish = os.environ.get('TRIGGER_EVENT') == 'workflow_dispatch' or needed('.', sha)
    result = f'publish={str(publish).lower()}\n'
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
        stream.write(result)
    print(result, end='')
