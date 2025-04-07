from datetime import datetime, timedelta, timezone

def trinidad_now():
    """
    Returns the current time offset to represent Trinidad time (UTC-4).
    Note: This returns a 'naive' datetime object (no explicit timezone info attached).
    For timezone-aware objects, consider using timezone/zoneinfo.
    """
    # 1. Get the current time in UTC
    utc_now = datetime.utcnow() # Or datetime.now(timezone.utc) for aware object

    # 2. Define the offset for Trinidad (UTC-4)
    trinidad_offset = timedelta(hours=-4)

    # 3. Apply the offset to the UTC time
    trinidad_time_now = utc_now + trinidad_offset

    # 4. Return the calculated time
    return trinidad_time_now

# Your other functions seem logically correct for naive datetime conversion:
def convert_to_trinidad_time(utc_time):
    """
    Converts a naive UTC datetime object to naive Trinidad time (UTC-4)
    """
    if utc_time is None:
        return None
    # Ensure input is naive if mixing aware/naive (or handle appropriately)
    if utc_time.tzinfo is not None:
         # Decide how to handle aware datetime input. Convert to UTC naive? Raise error?
         # Example: Convert aware time to naive UTC before applying offset
         utc_time = utc_time.astimezone(timezone.utc).replace(tzinfo=None)
         # Or raise ValueError("Input utc_time should be naive")

    trinidad_offset = timedelta(hours=-4)  # UTC-4
    return utc_time + trinidad_offset

def convert_to_utc(trinidad_time):
    """
    Converts a naive Trinidad time datetime object (assumed UTC-4) to naive UTC
    """
    if trinidad_time is None:
        return None
    # Ensure input is naive
    if trinidad_time.tzinfo is not None:
        # Decide how to handle aware datetime input. Treat as UTC-4? Raise error?
        # Example: Assume it's already UTC-4 aware, convert to UTC aware, then make naive
        # fixed_offset = timezone(timedelta(hours=-4))
        # utc_time = trinidad_time.astimezone(timezone.utc).replace(tzinfo=None)
        # return utc_time
         raise ValueError("Input trinidad_time should be naive")


    utc_offset = timedelta(hours=4)  # UTC+4 (to reverse UTC-4)
    return trinidad_time + utc_offset

# --- Example Usage ---
now_in_trinidad = trinidad_now()
print(f"Current time in Trinidad (naive UTC-4): {now_in_trinidad}")

# Example conversion
some_utc_time = datetime.utcnow()
print(f"Original UTC time: {some_utc_time}")

converted_to_trini = convert_to_trinidad_time(some_utc_time)
print(f"Converted to Trinidad Time: {converted_to_trini}")

converted_back_to_utc = convert_to_utc(converted_to_trini)
print(f"Converted back to UTC: {converted_back_to_utc}")

# Verify (they should be very close, allowing for tiny execution time differences)
time_difference = abs(some_utc_time - converted_back_to_utc)
print(f"Difference after round trip: {time_difference}")

# --- Note on Timezone Aware Objects (Recommended Practice) ---
# Using timezone objects is generally better as it avoids ambiguity.
# Requires Python 3.9+ and 'tzdata' package for zoneinfo, or use 'pytz' package.

# Example using timezone (Python 3.2+) or zoneinfo (Python 3.9+)
try:
    # Preferred way using zoneinfo (Python 3.9+)
    import zoneinfo
    trinidad_tz = zoneinfo.ZoneInfo("America/Port_of_Spain")
except (ImportError, zoneinfo.ZoneInfoNotFoundError):
    # Fallback using fixed offset timezone (less robust if DST rules applied)
    print("Warning: zoneinfo/tzdata not available or 'America/Port_of_Spain' not found. Using fixed UTC-4 offset.")
    trinidad_tz = timezone(timedelta(hours=-4), "AST") # AST is Atlantic Standard Time

def trinidad_now_aware():
     """Returns the current time in Trinidad as a timezone-aware datetime object."""
     return datetime.now(trinidad_tz)

def convert_to_trinidad_time_aware(dt_aware):
    """Converts a timezone-aware datetime object to Trinidad time."""
    if dt_aware is None:
        return None
    if dt_aware.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware")
    return dt_aware.astimezone(trinidad_tz)

def convert_to_utc_aware(dt_aware):
     """Converts a timezone-aware datetime object to UTC."""
     if dt_aware is None:
        return None
     if dt_aware.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware")
     return dt_aware.astimezone(timezone.utc)


print("\n--- Timezone-Aware Examples ---")
now_in_trinidad_aware = trinidad_now_aware()
print(f"Current time in Trinidad (aware): {now_in_trinidad_aware}")

utc_now_aware = datetime.now(timezone.utc)
print(f"Current time in UTC (aware): {utc_now_aware}")

converted_to_trini_aware = convert_to_trinidad_time_aware(utc_now_aware)
print(f"Converted UTC to Trinidad (aware): {converted_to_trini_aware}")

converted_back_to_utc_aware = convert_to_utc_aware(converted_to_trini_aware)
print(f"Converted Trinidad back to UTC (aware): {converted_back_to_utc_aware}")