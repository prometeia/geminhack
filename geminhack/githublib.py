from github import Github, Project
from yaml import dump
from sys import stderr


MAPTO = {
    "To do": "To do",
    "In progress": "In progress",
    "In review": "In progress",
    "Done": "Done"
}

TARGET_BOARD = "Current Sprint"


def get_col_dict(prj: Project) -> dict:
    return {col.name: col.node_id for col in prj.get_columns()}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("token")
    parser.add_argument("organization")
    args = parser.parse_args()
    g = Github(args.token)
    org = g.get_organization(args.organization)
    target = {}
    sources = {}
    for prj in org.get_projects():
        if prj.state != "open" or prj.name.startswith("Sprint"):
            continue
        if prj.name == TARGET_BOARD:
            target = get_col_dict(prj)
            continue
        for colname, colid in get_col_dict(prj).items():
            tg = MAPTO.get(colname)
            if not tg:
                continue
            sources.setdefault(tg, []).append(colid)
    assert target
    assert sources
    assert set(sources).issubset(set(target))
    steps = [
        {"uses": "actions/checkout@v2"}
    ]
    for srcname in sorted(sources):
        mstep = {
            "name": f"Mirroring column {srcname}",
            "uses": "jonabc/linked-project-columns@v1.1.0",
            "with": dict(
                github_token=r"${{ secrets.ORGS_TOKEN }}",
                source_column_id=', '.join(sorted(sources[srcname])),
                target_column_id=target[srcname]
            )
        }
        steps.append(mstep)
        print(f"Added {srcname} mirror step", file=stderr)
    action = dict(
        name="Sprint project mirroring",
        on=dict(schedule=[dict(cron= '*/5 * * * *')]),
        jobs=dict(sprint={
            "runs-on": "ubuntu-latest",
            "steps": steps
        })
    )
    print(dump(action))