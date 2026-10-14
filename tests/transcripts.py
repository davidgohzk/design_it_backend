"""The golden interviews from the frontend's complete examples (src/cases/*.seed.ts), with the facts
each client reply should disclose. Message indexes match the frontend's."""

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

# Handover WP2: msg 2 cr.current, msg 4 cr.scale, msg 6 cr.bookers, msg 8 cr.root-cause, msg 10 cr.staff.
COMMUNITY_ROOM_DISCLOSURES = {
    2: ["cr.current"],
    4: ["cr.scale"],
    6: ["cr.bookers"],
    8: ["cr.root-cause"],
    10: ["cr.staff"],
}

BRIGHTPATH_GOLDEN = [
    ("assistant", "Hi! I'm Sarah, program director at BrightPath NGO. We work with at-risk children and I'm hoping you can help us design a better system for our field teams. Feel free to ask me about the problem we're facing."),
    ("user", "Hi Sarah! Can you walk me through the main problem you're trying to solve?"),
    ("assistant", "Of course! Right now, when a field worker visits a child and notices something concerning - signs of neglect, an unsafe home, anything like that - they send a message in a WhatsApp group. The problem is the group has too many people, messages get buried, and there's no way to know if the right case manager actually saw it or is taking action. Sometimes alerts go unnoticed for a whole day. On top of that, when our NGO director has to report to donors or the government, we have no proper records - just old chat messages. It's really not working for us anymore."),
    ("user", "How many field workers and case managers are we dealing with? I need to understand the scale before proposing a design."),
    ("assistant", "We have about 40 field workers spread across three districts, and 12 case managers - each case manager is responsible for a group of field workers and their assigned children. On top of that, there are 3 supervisors who oversee everything and need to be looped in on high-severity incidents. On a busy day we might get 15 to 20 incident reports. It's not a huge volume, but the problem is that even one missed alert can have serious consequences for a child."),
    ("user", "What phones do your field workers carry?"),
    ("assistant", "Mostly low-end Android phones - nothing fancy."),
    ("user", "And what's the mobile signal like where they visit families?"),
    ("assistant", "Patchy, honestly. Out in the field the connection comes and goes, so they can't count on being online when they're with a family."),
    ("user", "When an alert goes out, who needs to see it, and what should happen if nobody responds?"),
    ("assistant", "The assigned case manager should get it straight away, and the supervisor too if it's serious. If nobody acknowledges it, it needs to be escalated - we can't have an alert just sitting there."),
]

BRIGHTPATH_DISCLOSURES = {
    2: ["brightpath.0", "brightpath.9"],
    4: ["brightpath.1", "brightpath.2", "brightpath.3", "brightpath.4"],
    6: ["brightpath.5"],
    8: ["brightpath.6"],
    10: ["brightpath.8"],
}


def as_history(transcript: list[tuple[str, str]], upto: int) -> list[dict]:
    """Messages 0..upto (inclusive) as chat turns."""
    return [{"role": role, "content": content} for role, content in transcript[: upto + 1]]
