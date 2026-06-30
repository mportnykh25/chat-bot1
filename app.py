"""
=====================================================================
WEEK 3 — CHATBOT THAT READS YOUR DOCUMENTS (Streamlit version)
=====================================================================

This is the Streamlit version of the chatbot we first built in Colab.
The CORE LOGIC is unchanged — same API call, same PDF extraction,
same idea of "memory = sending the full conversation back every time".

What's different is the DELIVERY MECHANISM:
Colab = a notebook you run cell by cell, with print()/input()
Streamlit = a real web app, with a UI, that anyone can open in a browser

Read the comments marked with tags below to understand WHY each
change exists:

  [REMOVED FROM COLAB]   -> this existed in Colab but is gone now
                             (it was Colab-specific, doesn't apply here)

  [NEW FOR STREAMLIT]    -> this didn't exist in Colab, but is
                             required for a Streamlit app to work

  [STREAMLIT-SPECIFIC]   -> this is special syntax/behavior that only
                             applies to Streamlit (not a general
                             programming concept — won't reuse this
                             exact pattern on, say, AWS/Flask)

  [GENERAL CONCEPT]      -> this is a real, transferable concept that
                             applies no matter what framework or cloud
                             platform you eventually use
=====================================================================
"""

import streamlit as st          # [NEW FOR STREAMLIT] the UI framework itself.
                                 # Colab didn't need this — Colab's UI was just
                                 # notebook cells, print(), and input().

from openai import OpenAI
import pdfplumber
import io


# =====================================================================
# [REMOVED FROM COLAB]
# These two lines existed in the Colab notebook and are GONE now:
#
#     from google.colab import files
#     from google.colab import userdata
#
# Why removed: these only exist inside the Google Colab environment.
# A regular Python file running on Streamlit Cloud (or anywhere else)
# does not have access to the `google.colab` package at all.
# =====================================================================


# ---------------------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------------------
# [NEW FOR STREAMLIT] — there was no "page" in Colab, just a notebook.
# Streamlit needs to know the page title (shown in the browser tab)
# and we add a title that displays at the top of the app.
# [STREAMLIT-SPECIFIC] syntax — this exact function only exists in Streamlit.
st.set_page_config(page_title="Chat with your Documents")
st.title("📄 Chat with your Documents")


# ---------------------------------------------------------------------
# API KEY SETUP
# ---------------------------------------------------------------------
# [GENERAL CONCEPT] Never hardcode API keys in your code. This applies
# everywhere — Colab, Streamlit, AWS, any production system.
#
# BEFORE (Colab):
#     OPENROUTER_API_KEY = userdata.get('OPENROUTER_API_KEY')
#     -> userdata.get() is a Colab-only feature (the key icon sidebar)
#
# AFTER (Streamlit):
#     We use st.secrets instead. On Streamlit Cloud, you set this value
#     in the app's dashboard settings (Settings -> Secrets), NOT in the
#     code, and NOT in a file that gets pushed to GitHub.
#
# [STREAMLIT-SPECIFIC] st.secrets is Streamlit's own secrets system.
# On AWS you'd use something like Secrets Manager or environment
# variables instead — different tool, same underlying idea.
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]

# The model we're using. "openrouter/free" automatically picks a free
# model for each request, so we don't need to track which specific
# free model is available this week (the free model list changes often).
MODEL = "openrouter/free"

# [GENERAL CONCEPT] Setting up the API client — this part is IDENTICAL
# to what we did in Colab. OpenRouter uses the same format as OpenAI,
# we just point the base_url at OpenRouter instead.
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


# ---------------------------------------------------------------------
# PDF TEXT EXTRACTION
# ---------------------------------------------------------------------
# [GENERAL CONCEPT] Extracting text from a PDF is the same logic as
# Colab — we still use pdfplumber, we still loop through pages.
#
# [NEW FOR STREAMLIT] The @st.cache_data decorator below.
# Why we need this: Streamlit reruns the ENTIRE script top to bottom
# every single time the user does anything (types a message, clicks
# a button, etc). Without caching, we would re-extract the PDF text
# on every single message sent — slow and wasteful.
# @st.cache_data tells Streamlit: "if the input hasn't changed, reuse
# the result instead of recomputing it."
# [STREAMLIT-SPECIFIC] this decorator is unique to Streamlit. In a
# normal backend (e.g. Flask on AWS) you'd extract the PDF once when
# it's uploaded and store the result in a database instead.
@st.cache_data
def extract_text_from_pdfs(uploaded_files):
    """
    Takes a list of uploaded PDF files and returns their combined text.
    """
    all_text = ""
    for uploaded_file in uploaded_files:
        # pdfplumber needs a file-like object — Streamlit's uploaded_file
        # already behaves like one, so no need to wrap it like we did
        # with io.BytesIO() in Colab (Colab gave us raw bytes instead).
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"
    return all_text


# ---------------------------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------------------------
# BEFORE (Colab):
#     uploaded = files.upload()
#     -> opens Colab's own file picker popup, returns a dict of
#        {filename: bytes}
#
# AFTER (Streamlit):
#     st.file_uploader() draws a real upload box in the web page.
#     It returns a list of file objects (or None if nothing uploaded yet)
# [STREAMLIT-SPECIFIC] syntax, but the IDEA of "let the user upload a
# file" is a general concept you'll see in every framework, just with
# different syntax (e.g. an <input type="file"> in plain HTML).
uploaded_files = st.file_uploader(
    "Upload one or more PDF documents",
    type="pdf",
    accept_multiple_files=True
)

# [NEW FOR STREAMLIT] We must explicitly check whether files were
# uploaded before doing anything else. In Colab, the notebook just
# paused and waited for files.upload() to finish — here, the script
# runs immediately even before a file is chosen, so we need this guard.
if not uploaded_files:
    st.info("Please upload at least one PDF to start chatting.")
    st.stop()  # [STREAMLIT-SPECIFIC] halts execution of the script here

# Extract the text (this will be instant on reruns thanks to caching)
document_text = extract_text_from_pdfs(uploaded_files)


# ---------------------------------------------------------------------
# CONVERSATION MEMORY (SESSION STATE)
# ---------------------------------------------------------------------
# BEFORE (Colab):
#     conversation_history = []
#     -> just a normal Python list. This worked fine in Colab because
#        the notebook cell ran ONE continuous `while True:` loop —
#        the variable stayed alive for the whole conversation.
#
# AFTER (Streamlit):
#     [NEW FOR STREAMLIT] Streamlit reruns the ENTIRE script from top
#     to bottom every time the user sends a message. If we used a
#     normal list here, it would reset to empty on every single rerun
#     — we'd lose the whole conversation after every message!
#
#     st.session_state is Streamlit's way of storing data that
#     SURVIVES across reruns, tied to the user's browser session.
#
# [STREAMLIT-SPECIFIC] st.session_state itself is unique to Streamlit.
# [GENERAL CONCEPT] underneath it, though: ANY real web app needs some
# way to persist state between requests (a database, a session table,
# a cache like Redis, cookies, etc). Streamlit just makes this trivially
# easy for prototyping — on AWS you'd build this part yourself.
if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------------------
# DISPLAY PAST MESSAGES
# ---------------------------------------------------------------------
# [NEW FOR STREAMLIT] This loop did not exist in Colab at all.
# In Colab, print() just appended new text below the previous output —
# old messages stayed on screen automatically.
#
# In Streamlit, because the WHOLE script reruns every time, the screen
# would go blank and only show the newest message unless we manually
# redraw every previous message first. So on every rerun, we loop
# through the saved history and redisplay each message.
# [STREAMLIT-SPECIFIC] st.chat_message() draws a styled chat bubble
# (user or assistant) — this is Streamlit's built-in chat UI component.
for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])


# ---------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------
# [GENERAL CONCEPT] Identical idea to Colab — we tell the model its
# role and give it the document text to ground its answers in.
system_message = f"""You are a helpful assistant that answers questions based on the provided documents.
Only answer based on the information in the documents below.
If the answer is not in the documents, say so clearly.
You can refer to previous questions and answers in the conversation.

--- DOCUMENTS ---
{document_text}
--- END OF DOCUMENTS ---"""


# ---------------------------------------------------------------------
# CHAT INPUT + RESPONSE
# ---------------------------------------------------------------------
# BEFORE (Colab):
#     while True:
#         user_input = input("You: ")
#         if user_input.lower() == "quit":
#             break
#         ...
#     -> Colab used an infinite loop that kept asking for input,
#        because input() blocks and waits right there in the cell.
#
# AFTER (Streamlit):
#     [NEW FOR STREAMLIT] There is NO while loop here at all.
#     st.chat_input() draws a chat box at the bottom of the page and
#     returns None until the user actually types something and hits
#     enter. Streamlit handles the "waiting" for us automatically by
#     re-running the script each time the user submits a message —
#     we don't write the loop ourselves.
# [STREAMLIT-SPECIFIC] st.chat_input() syntax itself, but [GENERAL
# CONCEPT] "wait for user input, then respond" applies everywhere.
user_input = st.chat_input("Ask a question about your documents...")

if user_input:
    # Show the user's new message immediately
    st.chat_message("user").write(user_input)

    # [GENERAL CONCEPT] Save it to history — same idea as Colab's
    # conversation_history.append(...), just stored in session_state
    # instead of a plain list so it survives the rerun.
    st.session_state.messages.append({"role": "user", "content": user_input})

    # [GENERAL CONCEPT] This API call is essentially IDENTICAL to Colab.
    # We send the system message + the full conversation history.
    # This is the actual "memory" mechanism — nothing magic, we are
    # just sending the whole conversation back to the model every time.
    with st.spinner("Thinking..."):  # [STREAMLIT-SPECIFIC] shows a loading spinner
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_message}
            ] + st.session_state.messages
        )
        assistant_reply = response.choices[0].message.content

    # Show the assistant's reply
    st.chat_message("assistant").write(assistant_reply)

    # Save the assistant's reply to history too
    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})


# =====================================================================
# RECAP — what actually changed vs Colab, at a glance:
#
#   REMOVED:    google.colab imports (files.upload, userdata.get)
#   REPLACED:   userdata.get()      -> st.secrets
#               files.upload()      -> st.file_uploader()
#               input()/print()     -> st.chat_input()/st.chat_message()
#               while True loop     -> Streamlit's rerun model (no loop!)
#               plain list          -> st.session_state (survives reruns)
#
#   ADDED (new ideas that didn't exist in Colab at all):
#               st.set_page_config / st.title  (a real page needs a UI)
#               @st.cache_data                 (avoid recomputing PDF text)
#               "redraw history" loop           (script reruns every time)
#               st.stop()                       (guard before files exist)
#
#   UNCHANGED (the real logic — this is what actually matters):
#               OpenAI client setup
#               PDF text extraction with pdfplumber
#               The system prompt
#               The API call structure
#               The idea that "memory" = resending the full conversation
# =====================================================================
