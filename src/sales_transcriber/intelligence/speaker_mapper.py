class SpeakerMapper:


    def __init__(self):

        self._mapping = {}


    def customer_speaker(self):

        if not self._mapping:

            return None

        return next(
            iter(
                self._mapping.values()
            )
        )