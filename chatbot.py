import base64
import multiprocessing
import os
import pprint
from datetime import datetime

import openai
import streamlit as st
import validators
from dotenv import load_dotenv
from PIL import Image
from streamlit_chat import message

from tools.login_checker import LoginChecker
import tldextract
import whois

def is_gov_or_corp_url(url):
    # List of known government and corporate domains
    GOV_DOMAINS = ["gov", "mil"]
    CORP_DOMAINS = ["com", "org", "net"]

    # Extract the top-level domain (TLD) of the URL
    ext = tldextract.extract(url)
    tld = ext.suffix

    # Check if the TLD matches a known government or corporate domain
    if tld in GOV_DOMAINS or tld in CORP_DOMAINS:
        return True
    else:
        return False

def is_gov_url(url):
    # Extract the domain name from the URL
    domain_name = url.split("//")[-1].split("/")[0]

    # Look up domain registration information using whois
    domain_info = whois.whois(domain_name)

    if domain_info:
        try:
            # Check if the domain belongs to a government entity
            if 'government' in domain_info.name.lower() or 'gov' in domain_info.name.lower():
                return True
        except Exception:
            pass
        
    return False
    
    
def is_gov_or_corp_website(url):
    # Check if the URL belongs to a government or corporate website
    if is_gov_or_corp_url(url) or is_gov_url(url):
        return True
    else:
        return False
    
# Change the webpage name and icon
web_icon_path = os.path.abspath("imgs/web_icon.png")
web_icon = Image.open(web_icon_path)
st.set_page_config(
    page_title="RedAGPT",
    page_icon=web_icon,
    initial_sidebar_state="expanded",
)

# Add audio player
audio_path = os.path.abspath("audio/blade_soundtrack.mp3")
audio_file = open(audio_path, "rb")
audio_bytes = audio_file.read()
st.sidebar.audio(audio_bytes, format="audio/mp3", start_time=0)

log_dict = {"lfp": None, "ssp": None}


def add_bg_from_local(image_file):
    with open(image_file, "rb") as f:
        img_bytes = f.read()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url('data:image/png;base64,{base64.b64encode(img_bytes).decode()}');
            background-size: cover;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# Add img to the bg
bg_img_path = os.path.abspath("imgs/bg_img.jpg")
add_bg_from_local(bg_img_path)


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = "https://chimeragpt.adventblocks.cc/api/v1"

st.markdown('<h1 style="color: white;">RedTeamAGPT</h1>', unsafe_allow_html=True)

if "show_first_chatbot_msg" not in st.session_state:
    st.session_state["show_first_chatbot_msg"] = True

if "set_local_or_remote" not in st.session_state:
    st.session_state["set_local_or_remote"] = False
if "user_local_remote" not in st.session_state:
    st.session_state["user_local_remote"] = None
if "edited_local_or_remote_msg_once" not in st.session_state:
    st.session_state["edited_local_or_remote_msg_once"] = False

if "show_url_msg_once" not in st.session_state:
    st.session_state["show_url_msg_once"] = False
if "showed_url_msg_once" not in st.session_state:
    st.session_state["showed_url_msg_once"] = False
if "showed_url_msg_once_checked" not in st.session_state:
    st.session_state["showed_url_msg_once_checked"] = False
if "save_url_msg" not in st.session_state:
    st.session_state["save_url_msg"] = None

# Initialize first msgs in the bot
if "bot_msgs" not in st.session_state:
    st.session_state["bot_msgs"] = ["Local OR Remote"]
if "user_msgs" not in st.session_state:
    st.session_state["user_msgs"] = []

if "allow_url_to_be_checked" not in st.session_state:
    st.session_state["allow_url_to_be_checked"] = False

if "seek_pos" not in st.session_state:
    st.session_state["seek_pos"] = None
if "process_started" not in st.session_state:
    st.session_state["process_started"] = False

# Set up the event flag for disabling the user input box
if "disable_input" not in st.session_state:
    st.session_state["disable_input"] = False

if "security_summary_success" not in st.session_state:
    st.session_state["security_summary_success"] = []
if "security_summary_failure" not in st.session_state:
    st.session_state["security_summary_failure"] = []


tools = ["Login Checker"]
model = st.selectbox("Tools", options=tools)

if model == "Login Checker":
    if not st.session_state["set_local_or_remote"]:
        placeholder = "Local or Remote"
    else:
        placeholder = "Enter URL here"

    if not st.session_state["disable_input"]:
        input_text = st.text_input(
            "", placeholder=placeholder, key="input_text", label_visibility="hidden"
        )
        st.session_state["user_msgs"].append(input_text)

        if not st.session_state["set_local_or_remote"]:  # Local or Remote

            if input_text == "Local" or input_text == "Remote":
                st.session_state[
                    "user_local_remote"
                ] = input_text  # save the user's input
                st.session_state["set_local_or_remote"] = True
                st.experimental_rerun()  # Rerun the script so the "Enter URL here" can be shown in the box
            else:
                # show this msg in the bot only if it's not the first msg of the bot
                if not st.session_state["show_first_chatbot_msg"]:
                    if not st.session_state["edited_local_or_remote_msg_once"]:
                        st.session_state["bot_msgs"][
                            -1
                        ] = "THE GIVEN INPUT IS INVALID.\nGIVE Local OR Remote"
                        st.session_state["edited_local_or_remote_msg_once"] = True
                    else:
                        st.session_state["bot_msgs"].append(
                            "THE GIVEN INPUT IS INVALID.\nGIVE Local OR Remote"
                        )

        else:  # Local or Remote has been set, now URL time

            # The bot should ask the user to give a url or ip based on their previous option
            if not st.session_state["show_url_msg_once"]:
                if st.session_state["user_local_remote"] == "Local":
                    msg = "GIVE URL"
                else:  # Remote
                    msg = "REMOTE SHOULD ONLY BE DONE ON IPs YOU OWN"

                width = 20
                padding = (width - len(msg)) // 8
                centered_text = f"<div style='text-align: center;'>{' ' * padding}{msg}{' ' * padding}</div>"
                decorative_lines = (
                    f"<div style='text-align: center;'>{'💀' * width}</div>"
                )

                # Combine the decorative lines and centered text
                msg = f"{decorative_lines * 2}<br>{centered_text}<br>{decorative_lines * 2}"

                # Streamlit gets confused here, so I assign the msg to a session
                # instead of doing len(st.session_state["bot_msgs"][-1])
                # where I show it on the bottom of the script
                st.session_state["save_url_msg"] = msg

                st.session_state["show_url_msg_once"] = True
                st.experimental_rerun()  # Rerun script to show the url msg in the bot

            if not st.session_state["allow_url_to_be_checked"]:
                # check for gov or corp

                if validators.url(input_text) and not is_gov_or_corp_website(input_text):
                    st.session_state["allow_url_to_be_checked"] = True
                else:
                    # Edit the url msg from "GIVE URL" TO "THE GIVEN URL IS INVALID"
                    # as we show one response from the bot and one from the user for each interaction
                    # and as we provide the "GIVE URL" to direct the user to give a url
                    # then won't be able to get a response by the bot based on the user's input
                    # thus, the needed change but it only need to be done once
                    if (
                        st.session_state["showed_url_msg_once"]
                        and not st.session_state["showed_url_msg_once_checked"]
                    ):
                        st.error("THE GIVEN URL IS INVALID OR FORBIDDEN!")
                        st.session_state["showed_url_msg_once_checked"] = True
                    else:
                        st.session_state["bot_msgs"].append("GOOD JOB. YOUR OPTION HAS BEEN SET.")

        if st.session_state["allow_url_to_be_checked"]:
            with st.spinner(f"Testing website {input_text}. This will take a while."):
                if not st.session_state["process_started"]:
                    lgcheck = LoginChecker(input_text)
                    process = multiprocessing.Process(
                        target=lgcheck.run()

                    )

                    process.start()
                    process.join()
                    st.session_state["process_started"] = True

                process.join()
                if not process.is_alive():
                    st.session_state["process_started"] = False

                    if os.path.exists(lgcheck.summary_file_path):
                        login_checker_msg = "Login Checker process has completed."

                        st.success(login_checker_msg)

                        # st.session_state["security_summary_success"].append(
                        #     login_checker_msg
                        # )

                        st.success(lgcheck.autogpt_resp)
        
                        # st.session_state["security_summary_success"].append(
                        #     lgcheck.autogpt_resp
                        # )

                        with open(lgcheck.summary_file_path, "r") as sectxt:
                            summary = "".join(sectxt.readlines())
                            st.success(summary)
                            # st.session_state["security_summary_success"].append(summary)

                    else:
                        login_checker_msg = "Login Check failed. No report found."
                        st.error(login_checker_msg)
                        # st.session_state["security_summary_failure"].append(
                        #     login_checker_msg
                        # )
                        
                        st.error(lgcheck.autogpt_resp)
                        # st.session_state["security_summary_failure"].append(
                        #     lgcheck.autogpt_resp
                        # )
                    
                    with st.expander("debug log"):
                        if os.path.exists(lgcheck.logging_file_path):
                            with open(lgcheck.logging_file_path, "r") as runtxt:
                                formatted_readlines = ''.join(runtxt.readlines())
                                st.write(formatted_readlines)

                st.session_state["disable_input"] = True  # Disable input
                # st.experimental_rerun()
    else:
        if len(st.session_state["security_summary_failure"]) != 0:
            st.error(st.session_state["security_summary_failure"])
        else:
            for item in st.session_state["security_summary_success"]:
                st.success(item)

        st.warning("SESSION EXPIRED.\nREFRESH THE PAGE.")


# Check that the security report is not created yet
if not st.session_state["disable_input"]:
    # Show the first msg in the chatbot
    if st.session_state["show_first_chatbot_msg"]:
        message(
            st.session_state["bot_msgs"], key=str(len(st.session_state["bot_msgs"]) - 1)
        )
        st.session_state["show_first_chatbot_msg"] = False

    else:  # all other times

        # Show the "GIVE URL" msg in the chatbot
        if (
            st.session_state["show_url_msg_once"]
            and not st.session_state["showed_url_msg_once"]
        ):
            st.session_state["bot_msgs"].append(st.session_state["save_url_msg"])
            # message(
            #     st.session_state["save_url_msg"],
            #     key=str(len(st.session_state["bot_msgs"])),
            # )
            st.markdown(st.session_state["save_url_msg"], unsafe_allow_html=True)

            st.session_state["showed_url_msg_once"] = True

        else:
            # Show all msgs after the first msg is already shown
            # Filter out any empty entry from the user
            filtered_user_msgs1 = [
                (i, msg)
                for i, msg in enumerate(st.session_state["user_msgs"])
                if len(msg) != 0
            ]
            filtered_bot_msgs1 = [
                (i, msg)
                for i, msg in enumerate(st.session_state["bot_msgs"])
                if len(msg) != 0
            ]

            # If the two lists do not have the same
            # Decrease the size of the longer list by one
            # so they can match
            filtered_user_msgs2 = filtered_user_msgs1
            filtered_bot_msgs2 = filtered_bot_msgs1
            if len(filtered_user_msgs1) > len(filtered_bot_msgs1):
                filtered_user_msgs2 = filtered_user_msgs1[:-1]
            elif len(filtered_user_msgs1) < len(filtered_bot_msgs1):
                filtered_bot_msgs2 = filtered_bot_msgs1[:-1]

            # Initialize the flag
            executed_once = False

            # Match the elements
            for (user_i, user_msg), (bot_i, bot_msg) in reversed(
                list(zip(filtered_user_msgs2, filtered_bot_msgs2))
            ):
                if not executed_once and (
                    len(filtered_user_msgs2) != len(filtered_bot_msgs2)
                ):
                    # Show the last element that was filtered above
                    if len(filtered_user_msgs2) > len(filtered_bot_msgs2):
                        message(
                            filtered_user_msgs2[user_i + 1][
                                1
                            ],  # Extract message text from the tuple
                            is_user=True,
                            key=str(user_i + 1) + "_user",
                        )
                    elif len(filtered_user_msgs2) < len(filtered_bot_msgs2):
                        message(
                            filtered_bot_msgs2[bot_i + 1][
                                1
                            ],  # Extract message text from the tuple
                            key=str(bot_i + 1),
                        )

                    # For showing the extra element only once and first in the conversation
                    executed_once = True

                # Print the matched elements
                message(user_msg, is_user=True, key=str(user_i) + "_user")
                message(bot_msg, key=str(bot_i))
