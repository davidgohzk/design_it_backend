"""The Community Room golden interview and its expected fact disclosures."""

COMMUNITY_ROOM_GOLDEN = [
    ("assistant", "Hi, I'm Mei — I run the front desk here at Bukit Cahaya Community Centre. Our room bookings have become a bit of a headache. Ask me anything!"),
    ("user", "Hi Mei! What happens today when someone wants to book a room?"),
    ("assistant", "They come to the front desk or call us, and we write it in the booking book. It's just a big paper book that stays at the desk. The trouble is we keep getting double bookings - two groups turn up for the same room at the same time, and someone always goes home upset."),
    ("user", "How many rooms do you have, and how many bookings do you get?"),
    ("assistant", "Three rooms - the activity hall, the meeting room and the dance studio. We get about 30 bookings a week, more during the school holidays."),
    ("user", "Who usually makes the bookings?"),
    ("assistant", "Mostly residents' groups - the seniors' exercise group, the tuition teachers, a few family events. Many of our regulars are elderly, and some of them don't have smartphones, so they call or just walk in."),
    ("user", "Why do you think the double bookings happen?"),
    ("assistant", "Hmm, I suppose it's usually the phone bookings. Whoever answers writes it on a sticky note because the book isn't always in front of them, and sometimes the note never makes it into the book."),
    ("user", "Who works at the desk?"),
    ("assistant", "Just me and one other staff member, on alternating shifts, and volunteers on weekends. We share the one computer at the desk."),
]

COMMUNITY_ROOM_DISCLOSURES = {
    2: ["cr.current"],
    4: ["cr.scale"],
    6: ["cr.bookers"],
    8: ["cr.root-cause"],
    10: ["cr.staff"],
}


def as_history(transcript: list[tuple[str, str]], upto: int) -> list[dict]:
    """Messages 0..upto (inclusive) as chat turns."""
    return [{"role": role, "content": content} for role, content in transcript[: upto + 1]]
