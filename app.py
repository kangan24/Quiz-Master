import streamlit as st
st.set_page_config(
    page_title="Quiz Master",
    page_icon="🤖",
    layout="wide"
) 

from dotenv import load_dotenv
import os
from google import genai
import json
from datetime import datetime
import pandas as pd

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("Gemini API key not found.")
    st.stop()
client = genai.Client(api_key=api_key)


# Session State
if "quiz" not in st.session_state:
    st.session_state.quiz = None

if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

if "score" not in st.session_state:
    st.session_state.score = 0

if "percentage" not in st.session_state:
    st.session_state.percentage = 0

if "feedback" not in st.session_state:
    st.session_state.feedback = ""

if "history_saved" not in st.session_state:
    st.session_state.history_saved = False


# Generate Quiz
def generate_quiz(topic, difficulty):

    prompt = f"""
    Generate exactly 5 MCQ questions about {topic}.

    Difficulty: {difficulty}

    Return ONLY valid JSON in this format:

    [
        {{
            "question": "Question text",
            "options": {{
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D"
            }},
            "answer": "A",
            "explanation": "Explanation here in exactly 1 or 2 lines"
        }}
    ]
    """

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

    except Exception as e:

        st.error(f"Error generating quiz: {e}")
        return []

    try:

        quiz = json.loads(response.text)
        return quiz

    except json.JSONDecodeError:

        st.error("Failed to parse quiz data.")
        return []


#  AI Feedback
def generate_feedback(topic, difficulty, score, total_questions):

    percentage = (score / total_questions) * 100

    report_prompt = f"""
    The user completed a quiz.

    Topic: {topic}
    Difficulty: {difficulty}

    Score: {score}/{total_questions}
    Percentage: {percentage:.2f}%

    Provide:
    1. A short performance review.
    2. Strengths.
    3. Areas to improve.

    Keep it under 100 words point wise.
    """

    report = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=report_prompt
    )

    return report.text


# STREAMLIT UI

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose Page",
    ["Quiz", "History"]
)

# HISTORY PAGE
if page == "History":

    st.title("📊 Quiz History")

    try:

        rows = []

        with open("quiz_history.txt", "r") as file:

            for line in file:

                parts = line.strip().split(" | ")

                if len(parts) == 5:

                    rows.append(parts)

        if rows:

            df = pd.DataFrame(
                rows,
                columns=[
                    "Date",
                    "Topic",
                    "Difficulty",
                    "Score",
                    "Percentage"
                ]
            )


            best_score = max(
                float(str(x).replace("%", ""))
                for x in df["Percentage"]
            )

            avg_score = sum(
                float(str(x).replace("%", ""))
                for x in df["Percentage"]
            ) / len(df)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Total Quizzes",
                    len(df)
                )

            with col2:
                st.metric(
                    "Best Score",
                    f"{best_score:.2f}%"
                )

            with col3:
                st.metric(
                    "Average Score",
                    f"{avg_score:.2f}%"
                )

            st.dataframe(
                df,
                use_container_width=True
            )

        else:
            st.info("No quiz attempts yet.")

    except FileNotFoundError:
        st.info("No quiz history found.")

    st.stop()

# QUIZ PAGE

st.title("🤖 Quiz Master")

topic = st.text_input("Enter Topic")

difficulty = st.selectbox(
    "Choose Difficulty",
    ["Easy", "Medium", "Hard"]
)

# Generate Quiz Button
if st.button("Generate Quiz"):

    if not topic:

        st.warning("Please enter a topic.")

    else:

        with st.spinner("Generating Quiz..."):

            st.session_state.quiz = generate_quiz(
                topic,
                difficulty
            )

            st.session_state.quiz_submitted = False
            st.session_state.score = 0
            st.session_state.percentage = 0
            st.session_state.feedback = ""
            st.session_state.history_saved = False


# Display Quiz
if st.session_state.quiz:

    for i, q in enumerate(
        st.session_state.quiz,
        start=1
    ):

        st.subheader(f"Question {i}/5")

        st.write(q["question"])

        st.radio(
            "Choose your answer:",
            options=list(q["options"].keys()),
            format_func=lambda x:
                f"{x}. {q['options'][x]}",
            key=f"q{i}"
        )

        st.divider()

    # Submit Button
    if st.button("Submit Quiz"):
        st.session_state.quiz_submitted = True

    # results
    if st.session_state.quiz_submitted:

        score = 0

        st.subheader("Results")

        for i, q in enumerate(
            st.session_state.quiz,
            start=1
        ):

            user_answer = st.session_state[f"q{i}"]

            if user_answer == q["answer"]:

                score += 1

                st.success(
                    f"Question {i}: Correct"
                )

            else:

                st.error(
                    f"Question {i}: Wrong"
                )

                st.write(
                    f"Your Answer: {user_answer}"
                )

                st.write(
                    f"Correct Answer: {q['answer']}"
                )

                st.info(
                    f"Explanation: {q['explanation']}"
                )

        st.session_state.score = score

        st.session_state.percentage = (
            score / len(st.session_state.quiz)
        ) * 100

        st.markdown("---")

        st.subheader(
            f"Score: {score}/{len(st.session_state.quiz)}"
        )

        st.write(
            f"Percentage: {st.session_state.percentage:.2f}%"
        )

        # feedback
        if not st.session_state.feedback:

            st.session_state.feedback = generate_feedback(
                topic,
                difficulty,
                score,
                len(st.session_state.quiz)
            )

        st.subheader("🤖 AI Feedback")

        st.write(st.session_state.feedback)

        st.markdown("---")

        
        # history
        if not st.session_state.history_saved:
            with open("quiz_history.txt", "a") as file:

                file.write(
                    f"{datetime.now():%Y-%m-%d %H:%M} | "
                    f"{topic} | "
                    f"{difficulty} | "
                    f"{score}/{len(st.session_state.quiz)} | "
                    f"{st.session_state.percentage:.2f}%\n"
                )
            st.session_state.history_saved = True


        # new quiz
        if st.button("🔄 Start New Quiz"):

            st.session_state.quiz = None
            st.session_state.quiz_submitted = False
            st.session_state.score = 0
            st.session_state.percentage = 0
            st.session_state.feedback = ""
            st.session_state.history_saved = False

            keys_to_remove = [
                key
                for key in list(st.session_state.keys())
                if key.startswith("q")
            ]

            for key in keys_to_remove:
                del st.session_state[key]

            st.rerun()