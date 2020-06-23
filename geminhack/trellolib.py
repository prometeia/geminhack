from trello import TrelloClient

# https://github.com/sarumont/py-trello

ROADMAP_BOARD_NAME = 'Roadmap'

class TrelloAPI(object):

    def __init__(self, api_key, api_secret, board_id=None):
        self.client = TrelloClient(api_key=api_key, api_secret=api_secret)
        if not board_id:
            for aboard in self.client.list_boards(board_filter='open'):
                if aboard.name == ROADMAP_BOARD_NAME:
                    board_id = aboard.id
        assert board_id
        self.board = self.client.get_board(board_id)

    @property
    def roadmap(self):
        return self.board.open_lists()

    @property
    def epics(self):
        return {c.name: c for c in self.board.open_cards()}
    