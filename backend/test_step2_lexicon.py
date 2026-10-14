"""Test suite for Step 2 Topic Lexicon.
Tests 5 paraphrases per topic with typos across all 4 programmes.
"""
import sys
sys.path.insert(0, "backend")

from app.conversation import analyze_turn
from app.lexicon import detect_primary_topic, score_topics

test_cases = [
    # Attendance
    ("is attndance compuslory for bca webinars?", "bca", "attendance"),
    ("do i need to atend live sessions for mba?", "mba", "attendance"),
    ("how is webinar attendence tracked in bba?", "bba", "attendance"),
    ("are mca online lectures mandtory to attend?", "mca", "attendance"),
    ("presense in live class for bca degree", "bca", "attendance"),

    # Schedule
    ("what is the class timng for bca?", "bca", "schedule"),
    ("when are mba lecturs held?", "mba", "schedule"),
    ("daily timetabl for bba online", "bba", "schedule"),
    ("what time do mca classes start?", "mca", "schedule"),
    ("weekly lectur routine for bba students", "bba", "schedule"),

    # Internship / Projects
    ("is there any intership in bca curriculum?", "bca", "internship_projects"),
    ("mba industrial trainng and project work", "mba", "internship_projects"),
    ("bba organizational attchment programme details", "bba", "internship_projects"),
    ("mca final semster disertation and live project", "mca", "internship_projects"),
    ("capston project for bca online course", "bca", "internship_projects"),

    # Scholarship
    ("is scolaship available for bca?", "bca", "scholarship"),
    ("any fee concssion for bba students?", "bba", "scholarship"),
    ("financial aid and fee waivr for mba", "mba", "scholarship"),
    ("merit scolership for mca program", "mca", "scholarship"),
    ("discount on bba tuition fee for girls", "bba", "scholarship"),

    # Taxes / Hidden charges
    ("is gst includd in bca fee?", "bca", "taxes_hidden_charges"),
    ("are there any hiden charges for mba?", "mba", "taxes_hidden_charges"),
    ("extra chargs besides bba tuition fee", "bba", "taxes_hidden_charges"),
    ("mca cours fee taxes and service charges", "mca", "taxes_hidden_charges"),
    ("additional unannounced expnses in bca", "bca", "taxes_hidden_charges"),

    # Faculty
    ("who are the bca faculti members?", "bca", "faculty"),
    ("list of mba teachrs and professors", "mba", "faculty"),
    ("who teaches bba online subjects?", "bba", "faculty"),
    ("mca instructrs and lecturer profile", "mca", "faculty"),
    ("course professrs teaching bca", "bca", "faculty"),

    # Mentor
    ("who is the course mentr for bca?", "bca", "mentor"),
    ("academic counselng contact for bba", "bba", "mentor"),
    ("how to reach mba academic advisr?", "mba", "mentor"),
    ("mca student guidance mentr name", "mca", "mentor"),
    ("counsellor for online degree students", "", "mentor"),

    # Student ID
    ("will i get a studnt id card in bca?", "bca", "student_id"),
    ("how to obtain physical identity crd for mba?", "mba", "student_id"),
    ("smart crd or id proof for bba student", "bba", "student_id"),
    ("mca digital identity crd issuance", "mca", "student_id"),
    ("student id crd dispatch process", "", "student_id"),

    # Certificate
    ("when will i get degree certifcate for bca?", "bca", "certificate"),
    ("convocatin and degree awarding for mba", "mba", "certificate"),
    ("bba provisonal pass certificate", "bba", "certificate"),
    ("mca graduatin certificate after completion", "mca", "certificate"),
    ("how to obtain original degree certficate?", "", "certificate"),

    # Technical issues
    ("lms logn error in bca portal", "bca", "technical_issues"),
    ("forgt my password for mba student login", "mba", "technical_issues"),
    ("technicl support for bba portal not loading", "bba", "technical_issues"),
    ("mca website lms errr while accessing", "mca", "technical_issues"),
    ("portal logn problem and password resst", "", "technical_issues"),

    # International / WES
    ("is bca eligble for wes evaluaton?", "bca", "international_wes"),
    ("can nri or foriegn student apply for mba?", "mba", "international_wes"),
    ("is bba degree acceptd abroad for higher studies?", "bba", "international_wes"),
    ("mca wes verifcation through portal", "mca", "international_wes"),
    ("internatinal admission requirements", "", "international_wes"),

    # Entrance test
    ("is there any entrnce exam for bca?", "bca", "entrance_test"),
    ("mba admissin test or cmat required?", "mba", "entrance_test"),
    ("do i have to give entranc test for bba?", "bba", "entrance_test"),
    ("mca competetive exam for admission", "mca", "entrance_test"),
    ("is cat or mat entrnce required for mba?", "mba", "entrance_test"),

    # EMI
    ("can i pay bca fee in emi?", "bca", "emi"),
    ("is zero intrest emi option for mba?", "mba", "emi"),
    ("monthly instllment facility for bba fee", "bba", "emi"),
    ("educaton loan and emi for mca course", "mca", "emi"),
    ("can fees be paid through monthli emi?", "", "emi"),

    # Assignments
    ("how to submtt bca assignmnts on lms?", "bca", "assignments"),
    ("what is the weightge of mba continuous assessmnt?", "mba", "assignments"),
    ("bba homewrk and internal assessmnt marks", "bba", "assignments"),
    ("mca internl marks and quiz submissin", "mca", "assignments"),
    ("internal evaluaton component in online degree", "", "assignments"),

    # Mobile
    ("is there a mobil app for bca classes?", "bca", "mobile"),
    ("can i watch mba lecturs on smartphon or tablet?", "mba", "mobile"),
    ("android or ios app for bba online lms", "bba", "mobile"),
    ("attend mca classes using mobil phon", "mca", "mobile"),
    ("dedicatd mobile applicaton for students", "", "mobile"),

    # Refund
    ("what is the refnd policy if i cancel bca?", "bca", "refund"),
    ("can i get mony back after mba cancellaton?", "mba", "refund"),
    ("bba fee refundabl rules on withdrawl", "bba", "refund"),
    ("how much fee is refundd if mca admissin cancelled?", "mca", "refund"),
    ("admissin cancellatn and fee refund percentge", "", "refund")
]

passed = 0
failed = 0

for q, expected_prog, expected_topic in test_cases:
    plan = analyze_turn(q)
    topic = plan.topic
    has_prog = (
        any(expected_prog in p for p in plan.programmes)
        if expected_prog
        else True
    )
    
    # Check if detected topic matches expected
    if topic == expected_topic and has_prog:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: '{q}' -> got topic='{topic}', progs={plan.programmes} (expected topic='{expected_topic}', prog='{expected_prog}')")

print(f"\nStep 2 Paraphrase Test: {passed}/{len(test_cases)} PASSED, {failed} FAILED.")
if failed > 0:
    sys.exit(1)
