#!/usr/bin/env python3
import subprocess
import ast
import pycountry
from flask import Flask, render_template

app = Flask(__name__)

# In case ufw status doesn't find any banned IPs.
F2BJAILS = ["sshd"]


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


# Process ufw status (or fail2ban as fallback), get IP addresses, and map them to ISO3 country codes.
def get_ip_origin_with_flags():
    # First, try to get IPs from "ufw status" (looking for lines with "REJECT")
    result = subprocess.run(["sudo", "ufw", "status"], stdout=subprocess.PIPE)
    ufw_output = result.stdout.decode("utf-8")

    # Extract the IP addresses from lines containing "REJECT"
    ip_addresses = [
        line.split()[2] for line in ufw_output.splitlines() if "REJECT" in line
    ]

    # If no banned IPs were found with ufw, try fail2ban for each jail in F2BJAILS
    if not ip_addresses:
        for jail in F2BJAILS:
            fail2ban_result = subprocess.run(
                ["sudo", "fail2ban-client", "get", jail, "banned"],
                stdout=subprocess.PIPE,
            )
            fail2ban_output = fail2ban_result.stdout.decode("utf-8").strip()
            # The output is something like:
            # ['103.101.160.198', '103.116.177.252', ...]
            try:
                jail_ips = ast.literal_eval(fail2ban_output)
                # If parsing doesn't return a list, make sure we get an empty list.
                if not isinstance(jail_ips, list):
                    jail_ips = []
            except Exception:
                jail_ips = []
            ip_addresses += jail_ips

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
