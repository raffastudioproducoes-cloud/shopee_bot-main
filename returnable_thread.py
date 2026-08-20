from threading import Thread


class ReturnableThread(Thread):
    def __init__(self, target, args=()):
        Thread.__init__(self)
        self.target = target
        self.result = None
        self.args = args

    def run(self) -> None:
        self.result = self.target(*self.args)
