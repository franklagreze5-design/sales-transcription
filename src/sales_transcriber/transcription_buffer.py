from __future__ import annotations


class TranscriptionBuffer:

    def __init__(
        self,
        max_messages: int = 20,
    ) -> None:

        self._messages: list[str] = []
        self._max_messages = max_messages


    def add(
        self,
        text: str,
    ) -> None:

        if not text.strip():
            return

        self._messages.append(
            text.strip()
        )

        if len(self._messages) > self._max_messages:

            self._messages = self._messages[
                -self._max_messages:
            ]


    def get_text(self) -> str:

        return "\n".join(
            self._messages
        )


    def clear(self) -> None:

        self._messages.clear()


    def size(self) -> int:

        return len(
            self._messages
        )