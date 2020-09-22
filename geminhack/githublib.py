from github import Github, Project
from yaml import dump
from sys import stderr


MAPTO = {
    "To do": "To do",
    "In progress": "In progress",
    "In review": "In progress",
    "Done": "Done",
    "Obsolete": None,
    "Backlog": None
}

TARGET_BOARD = "Current Sprint"


class GitHubBoarder(object):

    def __init__(self, token: str, organization: str):
        self.g = Github(token)
        self.org = self.g.get_organization(organization)

    def get_board(self, name: str):
        for prj in self.org.get_projects():
            if prj.name == name:
                return prj

    @staticmethod
    def get_col_dict(prj: Project) -> dict:
        return {col.name: col.node_id for col in prj.get_columns()}                

    def create_clone_action(self):
        target = {}
        sources = {}
        for prj in self.org.get_projects():
            if prj.state != "open" or prj.name.startswith("Sprint"):
                continue
            if prj.name == TARGET_BOARD:
                target = self.get_col_dict(prj)
                continue
            for colname, colid in self.get_col_dict(prj).items():
                if colname not in MAPTO:
                    print(f"WARNING: Unknown source column '{colname}' on board '{prj.name}'", file=stderr)
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
                "uses": "jonabc/linked-project-columns@v1.1.1",
                "with": dict(
                    github_token=r"${{ secrets.ORGS_TOKEN }}",
                    source_column_id=', '.join(sorted(set(sources[srcname]))),
                    target_column_id=target[srcname],
                    add_note=False
                )
            }
            steps.append(mstep)
            print(f"Added {srcname} mirror step", file=stderr)
        action = dict(
            name="Sprint project mirroring",
            on=dict(
                schedule=[dict(cron='*/30 06-19 * * 1-5')],
                push=dict(branchs=["master"])
            ),
            jobs=dict(sprint={
                "runs-on": "ubuntu-latest",
                "steps": steps
            })
        )
        return action



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("token")
    parser.add_argument("organization")
    args = parser.parse_args()
    gb = GitHubBoarder(args.token, args.organization)
    print(dump(gb.create_clone_action()))
