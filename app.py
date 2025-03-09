#!/usr/bin/env python3
import subprocess
import pycountry
from flask import Flask, render_template

app = Flask(__name__)


# Given an IP, return the two-letter country code from geoiplookup.
def get_country(ip):
    result = subprocess.run(["geoiplookup", ip], stdout=subprocess.PIPE)
    output = result.stdout.decode("utf-8")
    try:
        # Expecting output like "GeoIP Country Edition: US, United States"
        country_info = output.split(":")[1].strip()
        two_letter = country_info.split()[0].replace(",", "")
        if two_letter.isalpha() and len(two_letter) == 2:
            return two_letter.upper()
        else:
            return None
    except IndexError:
        return None


# Convert a 2-letter ISO code to a 3-letter ISO code in uppercase.
def alpha3(country_code):
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        if country:
            return country.alpha_3  # Return in uppercase (e.g. "USA")
        else:
            return country_code.upper()
    except Exception:
        return country_code.upper()


# Process ufw status, get IP addresses, and map them to ISO3 country codes.
def get_ip_origin_with_flags():
    result = subprocess.run(["sudo", "ufw", "status"], stdout=subprocess.PIPE)
    ufw_output = result.stdout.decode("utf-8")

    # Extract the IP addresses from lines containing "REJECT"
    ip_addresses = [
        line.split()[2] for line in ufw_output.splitlines() if "REJECT" in line
    ]

    country_count = {}
    for ip in ip_addresses:
        code = get_country(ip)
        if code:
            iso3 = alpha3(code)
            country_count[iso3] = country_count.get(iso3, 0) + 1

    total = sum(country_count.values())
    # Build a list of tuples: (ISO3 code, count, percentage)
    country_percentage = [
        (country, count, (count / total) * 100 if total else 0)
        for country, count in country_count.items()
    ]
    # Sort descending by percentage (i.e., third tuple element)
    country_percentage.sort(key=lambda tup: tup[2], reverse=True)
    return country_percentage


@app.route("/")
def home():
    country_data = get_ip_origin_with_flags()
    return render_template("index.html", country_data=country_data)


if __name__ == "__main__":
    app.run(debug=True)

# eof
