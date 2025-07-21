from typing import Iterator, Sequence

import discord


def pagify(
    text: str,
    delims: Sequence[str] = ["\n"],
    *,
    priority: bool = False,
    escape_mass_mentions: bool = True,
    shorten_by: int = 8,
    page_length: int = 2000,
) -> Iterator[str]:
    in_text = text
    page_length -= shorten_by
    while len(in_text) > page_length:
        this_page_len = page_length
        if escape_mass_mentions:
            this_page_len -= in_text.count("@here", 0, page_length)
            this_page_len -= in_text.count("@everyone", 0, page_length)

        # First generate a list of delim positions
        delim_positions = [in_text.rfind(d, 1, this_page_len) for d in delims]

        if priority:
            # Find the first delim that's > 0, or fallback to -1
            closest_delim = next((x for x in delim_positions if x > 0), -1)
        else:
            closest_delim = max(delim_positions)

        # Fallback if no delimiter found
        closest_delim = closest_delim if closest_delim != -1 else this_page_len

        if escape_mass_mentions:
            to_send = escape(in_text[:closest_delim], mass_mentions=True)
        else:
            to_send = in_text[:closest_delim]

        if to_send.strip():
            yield to_send

        in_text = in_text[closest_delim:]

    if in_text.strip():
        if escape_mass_mentions:
            yield escape(in_text, mass_mentions=True)
        else:
            yield in_text


def escape(text: str, *, mass_mentions: bool = False, formatting: bool = False) -> str:
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = discord.utils.escape_markdown(text)
    return text
