<h1 align="center">
  <img src="docs/icon_test.jpg" alt="Project Icon" width="150">
  <br>
  luogu-api-python
</h1>

<div align="center" style="display: flex; justify-content: center; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">
  <a href="#"><img alt="Python Version" src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge"></a>
  <a href="#"><img alt="License" src="https://img.shields.io/badge/License-GPLv3-green?style=for-the-badge"></a>
  <a href="#"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/luogu-api-python?style=for-the-badge"></a>
</div>

luogu-api-python is a Python implementation of the Luogu API. It provides an interface to interact with the Luogu online judge system, allowing users to programmatically manage problems and user operations on Luogu. This library aims to simplify automating tasks on Luogu with easy-to-use methods and classes.

Upstream docs: [https://github.com/sjx233/luogu-api-docs](https://github.com/sjx233/luogu-api-docs)

## Installation

To install the package, use pip:

```console
$ pip3 install luogu-api-python
```

To install the package from source, follow these steps:

```console
$ git clone https://github.com/NekoOS-Group/luogu-api-python.git
$ cd luogu-api-python
$ python3 -m pip install .
```

## Usage

### Synchronous API

```python
import pyLuogu

luogu = pyLuogu.luoguAPI()

problems = luogu.get_problem_list().problems
for problem in problems:
    print(problem.title)
```

Authenticated endpoints need Luogu cookies:

```python
import pyLuogu

cookies = pyLuogu.LuoguCookies({
    "__client_id": "...",
    "_uid": "...",
})

luogu = pyLuogu.luoguAPI(cookies=cookies)
me = luogu.me()
print(me.name)
```

### Asynchronous API

`asyncLuoguAPI` mirrors the synchronous API surface. Method names and return
types are kept aligned with `luoguAPI`.

```python
import asyncio
import pyLuogu

luogu = pyLuogu.asyncLuoguAPI()

async def main():
    problems = (await luogu.get_problem_list()).problems
    for problem in problems:
        print(problem.title)

asyncio.run(main())
```

Use `async with` when you want the HTTP client to close automatically:

```python
async with pyLuogu.asyncLuoguAPI() as luogu:
    contest = await luogu.get_contest(1)
```

## Docs

- API reference: [docs/api_reference.md](docs/api_reference.md)
- Static API viewer: [docs/api_viewer.html](docs/api_viewer.html)
- Machine-readable API metadata: [docs/api_reference.json](docs/api_reference.json)
- Discovered endpoint manifest: [docs/luogu-api-discovered.json](docs/luogu-api-discovered.json)
- Upstream TypeScript definitions: <https://0f-0b.github.io/luogu-api-docs/luogu-api.d.ts>
- The Python API keeps user-friendly names where practical, so method names do
  not always match upstream field names one-to-one.

## API Coverage

The documented/discovered Luogu endpoints are exposed as explicit methods on
both `luoguAPI` and `asyncLuoguAPI`. The current implementation covers these
areas:

- Activities / benben: list, watching feed, post, delete, report
- Articles: list, mine, favored, collections, create, edit, delete, batch edit,
  favor, vote, promotion requests, replies
- Auth and OpenID low-level endpoints: captcha, password/TOTP/MOTP auth,
  register verification, lock/unlock, logout, bind/connect/unbind OpenID
- Blogs: list, detail, create, edit, delete, replies, vote, admin list actions
- Chat: page, records, send, delete, clear unread
- Contests: list, detail, created detail, joined list, scoreboard, join, squad,
  create, edit, edit problems, delete
- Discussions: list, detail, created posts, post, reply, delete, report
- Images: list, detail, upload-link generation, delete
- Problems: list, detail, settings, create, edit, testcase settings, transfer,
  delete, solutions, tasklist, submit, translate
- Problem sets / trainings: list, detail, marked list, mark/unmark, create,
  edit, add/edit problems, clone, delete
- Records: list, detail, downloadable testcase query, testcase download
- Teams: detail, member/problem/training/contest pages, join, exit, create,
  edit, notice/member management, review, kick
- Themes: list, design, set, create, edit, delete
- Users: profile, info, followings, followers, blacklist, search, practice,
  settings, preferences, prize/security settings, slogan/introduction/header,
  VJudge binding
- Miscellaneous: config, rankings, notifications, advertisements, paintboard,
  paste, tags

Most stable endpoints return typed response objects from `pyLuogu.types`.
Endpoints whose response shape is still loose or varies between templates
return `RawDataResponse`; the raw payload is available as `.data`.

The following are convenience helpers, not separate discovered endpoint
wrappers, and are still intentionally left for future work:

- `login`
- `download_testcases`
- `upload_testcases`
- `submit_code_via_openluogu`

`logout` is implemented through the documented `/auth/logout` endpoint.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

### Pull Request

1. Fork the repository on GitHub.
2. Clone your forked repository to your local machine:
    ```commandline
    $ git clone https://github.com/your-username/luogu-api-python.git
    $ cd luogu-api-python
    ```
3. Create a new branch for your feature or bugfix:
    ```commandline
    $ git checkout -b feature-or-bugfix-name
    ```
4. Make your changes and commit them with a descriptive commit message:
    ```commandline
    $ git add .
    $ git commit -m "Description of your changes"
    ```
5. Push your changes to your forked repository:
    ```commandline
    $ git push origin feature-or-bugfix-name
    ```
6. Open a pull request on the original repository and provide a detailed description of your changes.

### Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub. Provide as much detail as possible to help us understand and address the issue.

## Development

Run the local checks before submitting changes:

```console
$ python3 -m pyright pyLuogu tests
$ python3 -m unittest discover -s tests
$ python3 -m compileall -q pyLuogu
```

Regenerate the API reference and static viewer after changing public methods or
types:

```console
$ python3 scripts/generate_api_docs.py
```
