# startup-founder-analysis
 - Takes a Linkedin profile URL of a person object and throws i into a prompt for evaluation against a rubric for entrepreneurial orientation and gives a JSON format for entrepreneurial score (eo_score) is returned for each person along with reasons [] array on why a particular score (between 0-4) 

Exceptional Signals: Serial Health Tech Entrepreneur (SCORE = 4)
* 3+ health technology or AI/ML venture-backed companies founded as CEO/CTO/Founder/Co-Founder

Strong Signals: “Relevant Area” Founder or Serial Founder (SCORE = 3)
* Current or past CEO/CTO/Founder/Co-Founder of at least one health tech or AI/ML company that raised a venture round
* Multi-time founder of venture-backed companies (2+ companies as Founder/Co-Founder that raised a venture round)

Moderate Signals: Emerging Founder or Repeat Founding Team Member (SCORE = 2)
* Experience in a Founder/Co-Founder role, raising a venture round for their company
* Graduate from Y Combinator or similar accelerator as founder
* Current company listed as Stealth, Stealth Mode, or similar
* Dropped out of college with subsequent founding role
* Founder in Residence or Entrepreneur in Residence experience
* Multiple early employee experiences (employee #1-20 or pre-Series B with significant scope in each)

Low Signals: Entrepreneurial Exposure and Intent (SCORE = 1)
* Joined startup as new grad or within 2 years of graduation date shown
* Graduated from an accelerator program
* Currently uses "building," "0–1 builder," "launching" in bio/headline
* Published patents or mentions prototypes/MVPs in profile
* Blog/Substack about startup or technology ideas or "building in public"
* Single early employee experience at startup with significant technical, product, or commercial scope
* Member of entrepreneurship/innovation clubs at universities (StartX, MIT Sandbox, Harvard iLab, etc.)
* Hackathon or pitch competition participation mentioned in profile
* Intern at startup or venture-backed company
* Roles at venture studios, incubators, or new venture teams (e.g., Google X, Atomic, BCG Digital Ventures)
* Uses "entrepreneur," "founder," "builder" in headline/bio
* Lists "Advisor" or "Angel Investor" in profile
* Speaker at startup/innovation events listed in profile

No/Negative Entrepreneurial Signals (SCORE = 0)
* No significant signals of entrepreneurship or intent present
* Exclusively corporate or academic roles with no startup exposure
* No evidence of innovation, building, or entrepreneurial activities
* Only worked at established companies
* Negative signal: Demonstrated some entrepreneurial signal but moved to a big/lower-risk role (e.g., at a FAANG), especially if they transitioned between big and large companies multiple times

