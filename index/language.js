(() => {
  const languageKey = 'vipsathi.language';
  const translations = {
    'Home': 'गृहपृष्ठ',
    'Problem': 'समस्या',
    'How it works': 'यसले कसरी काम गर्छ',
    'Hazards': 'विपद् जोखिम',
    'Authorities': 'निकायहरू',
    'Coverage': 'कार्य क्षेत्र',
    'Log in': 'लग इन',
    'Log In': 'लग इन',
    'Sign in': 'साइन इन',
    'Sign In': 'साइन इन',
    'Sign up': 'दर्ता गर्नुहोस्',
    'Sign Up': 'दर्ता गर्नुहोस्',
    'Sign out': 'लग आउट',
    'Sign Out': 'लग आउट',
    'Log out': 'लग आउट',
    'Back to home': 'गृहपृष्ठमा फर्कनुहोस्',
    'Create an account': 'खाता खोल्नुहोस्',
    'Create account': 'खाता खोल्नुहोस्',
    'Overview': 'अवलोकन',
    'Live Cameras': 'प्रत्यक्ष क्यामेरा',
    'Live cameras': 'प्रत्यक्ष क्यामेरा',
    'Live Map': 'प्रत्यक्ष नक्सा',
    'Live map': 'प्रत्यक्ष नक्सा',
    'Incident Alerts': 'घटना सतर्कता',
    'Incident alerts': 'घटना सतर्कता',
    'Incident History': 'घटना इतिहास',
    'Incident history': 'घटना इतिहास',
    'Profile': 'प्रोफाइल',
    'Settings': 'सेटिङहरू',
    'Operations': 'सञ्चालन',
    'Systems operational': 'प्रणाली सञ्चालनमा छ',
    'Last sync': 'अन्तिम समक्रमण',
    'Last sync 18:42:09': 'अन्तिम समक्रमण १८:४२:०९',
    'Network': 'सञ्जाल',
    'Support': 'सहायता',
    'AUTHORITY OPERATIONS': 'अधिकारी सञ्चालन',
    '24/7 network monitoring': '२४/७ सञ्जाल निगरानी',
    'AI MONITORING': 'एआई निगरानी',
    'LIVE FEED': 'प्रत्यक्ष दृश्य',
    'Primary Feed · Integrated Laptop Camera (Index 0)': 'प्राथमिक दृश्य · ल्यापटप क्यामेरा (सूचकांक ०)',
    'Secondary Feed · External USB Webcam (Index 1)': 'दोस्रो दृश्य · बाह्य USB वेबक्याम (सूचकांक १)',
    '2 online · 0 offline': '२ अनलाइन · ० अफलाइन',
    'Kathmandu, Nepal': 'काठमाडौं, नेपाल',
    'Detect · Alert · Respond': 'पहिचान · सतर्कता · प्रतिक्रिया',
    'Detect · Alert · Respond.': 'पहिचान · सतर्कता · प्रतिक्रिया।',
    'All cameras': 'सबै क्यामेरा',
    'Active detection': 'सक्रिय पहिचान',
    'Primary': 'प्राथमिक',
    'Offline': 'अफलाइन',
    'ACTIVE': 'सक्रिय',
    'STANDBY': 'प्रतीक्षारत',
    'Search': 'खोज्नुहोस्',
    'Search Camera ID, location, or source': 'क्यामेरा आईडी, स्थान वा स्रोत खोज्नुहोस्',
    'Filter by status': 'अवस्थाअनुसार छान्नुहोस्',
    'Camera': 'क्यामेरा',
    'Cameras': 'क्यामेराहरू',
    'Camera network': 'क्यामेरा सञ्जाल',
    'Camera network and active incidents across the assigned area.': 'तोकिएको क्षेत्रमा क्यामेरा सञ्जाल र सक्रिय घटनाहरू।',
    '2 active surveillance cameras configured for operational monitoring.': 'सञ्चालन निगरानीका लागि २ सक्रिय क्यामेरा जडान गरिएका छन्।',
    'Bagmati Control Room': 'बागमती नियन्त्रण कक्ष',
    'Kathmandu Valley': 'काठमाडौं उपत्यका',
    'Authority Operations': 'अधिकारी सञ्चालन',
    'Resource network': 'स्रोत सञ्जाल',
    'Available Resources': 'उपलब्ध स्रोतहरू',
    'Resource Mapping': 'स्रोत नक्साङ्कन',
    'Emergency Contacts': 'आपत्कालीन सम्पर्कहरू',
    'Your विपद्Sathi': 'तपाईंको विपद्Sathi',
    'Citizen': 'नागरिक',
    'Authorities': 'निकायहरू',
    'Citizen account': 'नागरिक खाता',
    'Authority account': 'अधिकारी खाता',
    'Citizen reporting': 'नागरिक रिपोर्टिङ',
    'Citizen reports': 'नागरिक रिपोर्टहरू',
    'My reports': 'मेरा रिपोर्टहरू',
    'Notifications': 'सूचनाहरू',
    'Report an incident': 'घटना रिपोर्ट गर्नुहोस्',
    'Report another incident': 'अर्को घटना रिपोर्ट गर्नुहोस्',
    'Back to dashboard': 'ड्यासबोर्डमा फर्कनुहोस्',
    'My reports': 'मेरा रिपोर्टहरू',
    'Report details': 'रिपोर्ट विवरण',
    'What you reported': 'तपाईंले रिपोर्ट गर्नुभएको विवरण',
    'Response updates': 'प्रतिक्रिया अद्यावधिकहरू',
    'Report received': 'रिपोर्ट प्राप्त भयो',
    'Response team': 'प्रतिक्रिया टोली',
    'We will notify you when a response is dispatched.': 'प्रतिक्रिया टोली परिचालित भएपछि हामी तपाईंलाई जानकारी दिनेछौँ।',
    'Report ID': 'रिपोर्ट आईडी',
    'Submitted': 'पठाइएको',
    'Road accident': 'सडक दुर्घटना',
    'Mugling-Narayanghat Highway · Today, 10:24 AM': 'मुग्लिन-नारायणगढ राजमार्ग · आज, बिहान १०:२४',
    'Two vehicles collided near the highway curve. Traffic is partially blocked and emergency assistance may be needed.': 'राजमार्गको घुम्ती नजिक दुई सवारीसाधन ठोक्किएका छन्। यातायात आंशिक रूपमा अवरुद्ध छ र आपत्कालीन सहायता आवश्यक पर्न सक्छ।',
    'Today, 10:24 AM · विपद्Sathi received your report.': 'आज, बिहान १०:२४ · विपद्Sathi ले तपाईंको रिपोर्ट प्राप्त गर्‍यो।',
    'Today, 10:36 AM · The report is being verified.': 'आज, बिहान १०:३६ · रिपोर्ट पुष्टि हुँदैछ।',
    '← My reports': '← मेरा रिपोर्टहरू',
    'Mugling-Narayanghat Highway, Kilometer 42': 'मुग्लिन-नारायणगढ राजमार्ग, किलोमिटर ४२',
    'The report is being verified.': 'रिपोर्ट पुष्टि हुँदैछ।',
    'Continue to incident report': 'घटना रिपोर्टमा जानुहोस्',
    'Submit report': 'रिपोर्ट पठाउनुहोस्',
    'Incident type': 'घटनाको प्रकार',
    'Description': 'विवरण',
    'Location': 'स्थान',
    'Exact location': 'ठ्याक्कै स्थान',
    'Date and time': 'मिति र समय',
    'Date & time': 'मिति र समय',
    'Evidence': 'प्रमाण',
    'Choose a file': 'फाइल छान्नुहोस्',
    'Choose files': 'फाइलहरू छान्नुहोस्',
    'Attach photos straight from your phone as evidence': 'प्रमाणका लागि फोनबाटै तस्बिर संलग्न गर्नुहोस्',
    'Contact': 'सम्पर्क',
    'Phone number': 'फोन नम्बर',
    'Password': 'पासवर्ड',
    'Confirm password': 'पासवर्ड पुष्टि गर्नुहोस्',
    'Change password': 'पासवर्ड परिवर्तन गर्नुहोस्',
    'Email': 'इमेल',
    'Name': 'नाम',
    'Full name': 'पूरा नाम',
    'Department / unit': 'विभाग / इकाई',
    'Designation': 'पद',
    'District': 'जिल्ला',
    'Authority type': 'निकायको प्रकार',
    'Citizen sign up': 'नागरिक दर्ता',
    'Authority sign in': 'अधिकारी साइन इन',
    'Choose your role.': 'आफ्नो भूमिका छान्नुहोस्।',
    'Choose with care': 'ध्यानपूर्वक छान्नुहोस्',
    'Create your official account': 'आफ्नो आधिकारिक खाता खोल्नुहोस्',
    'Continue': 'अगाडि बढ्नुहोस्',
    'Cancel': 'रद्द गर्नुहोस्',
    'Save changes': 'परिवर्तनहरू सुरक्षित गर्नुहोस्',
    'Save settings': 'सेटिङहरू सुरक्षित गर्नुहोस्',
    'Update profile': 'प्रोफाइल अद्यावधिक गर्नुहोस्',
    'Request an information update': 'जानकारी अद्यावधिक गर्न अनुरोध गर्नुहोस्',
    'Overview': 'अवलोकन',
    'Dashboard': 'ड्यासबोर्ड',
    'Daily operational summary': 'दैनिक सञ्चालन सारांश',
    'Current status': 'हालको अवस्था',
    'Coverage active': 'कार्य क्षेत्र सक्रिय',
    'Critical incident alerts': 'गम्भीर घटना सतर्कताहरू',
    'Critical only': 'गम्भीर मात्र',
    'Critical': 'गम्भीर',
    'High': 'उच्च',
    'Medium': 'मध्यम',
    'Low': 'कम',
    'Detected': 'पहिचान भयो',
    'Camera detected': 'क्यामेराले पहिचान गर्‍यो',
    'Camera-assisted assessment': 'क्यामेरा-सहायित मूल्याङ्कन',
    'Detection ready': 'पहिचान तयार',
    'Dispatch response': 'प्रतिक्रिया टोली पठाउनुहोस्',
    'En route': 'बाटोमा',
    'Resolved': 'समाधान भयो',
    'Under review': 'समीक्षामा',
    'Awaiting authority review and field confirmation.': 'अधिकारीको समीक्षा र स्थलगत पुष्टिको प्रतीक्षामा।',
    'Automatic detection: collision pattern and stationary vehicles. Traffic is partially blocked in the eastbound lane.': 'स्वचालित पहिचान: ठक्करको ढाँचा र रोकिएका सवारीसाधन। पूर्वतर्फको लेनमा यातायात आंशिक रूपमा अवरुद्ध छ।',
    'Based on detected vehicle count, collision pattern, and lane obstruction.': 'पहिचान भएका सवारीसाधनको संख्या, ठक्करको ढाँचा र लेन अवरोधका आधारमा।',
    'False alert': 'गलत सतर्कता',
    'View details': 'विवरण हेर्नुहोस्',
    'Call Now': 'अहिले फोन गर्नुहोस्',
    'Fire': 'आगलागी',
    'Fire & Rescue': 'दमकल तथा उद्धार',
    'Fire brigade': 'दमकल सेवा',
    'Fire near roadway': 'सडकछेउ आगलागी',
    'Flood': 'बाढी',
    'Floods': 'बाढीहरू',
    'Landslide': 'पहिरो',
    'Landslides': 'पहिरोहरू',
    'Road accidents': 'सडक दुर्घटनाहरू',
    'Blocked road': 'अवरुद्ध सडक',
    'Blocked roads': 'अवरुद्ध सडकहरू',
    'What we detect': 'हामीले पहिचान गर्ने विपद्',
    'Built for the hazards Nepal\'s highways actually face.': 'नेपालका राजमार्गमा देखिने वास्तविक जोखिमका लागि निर्मित।',
    'When the highway turns dangerous, the right people know in seconds.': 'राजमार्गमा खतरा उत्पन्न हुँदा सम्बन्धित निकायले केही सेकेन्डमै जानकारी पाउँछन्।',
    'When the highway turns dangerous,': 'राजमार्गमा खतरा उत्पन्न हुँदा',
    'the right people know in seconds.': 'सम्बन्धित निकायले केही सेकेन्डमै जानकारी पाउँछन्।',
    'विपद्Sathi places cameras on Nepal\'s accident-prone bends, landslide corridors and fog-heavy stretches. The moment a crash or hazard is detected, an alert with location and footage reaches the nearest authority — long before a phone call could. Where no camera exists, any driver or bystander can report it directly from the app, with a photo as evidence.': 'विपद्Sathi ले नेपालका दुर्घटनाग्रस्त मोड, पहिरो जोखिम क्षेत्र र बाक्लो हुस्सु लाग्ने सडकमा क्यामेरा जडान गर्छ। दुर्घटना वा जोखिम पहिचान हुनासाथ स्थान र दृश्यसहितको सतर्कता नजिकको निकायमा पुग्छ। क्यामेरा नभएको ठाउँमा चालक वा प्रत्यक्षदर्शीले तस्बिरसहित एपबाटै रिपोर्ट गर्न सक्छन्।',
    'highway stretches': 'राजमार्गका खण्डहरू',
    'avg. alert time': 'औसत सतर्कता समय',
    'real-time monitoring': 'वास्तविक समय निगरानी',
    'Multi-vehicle collision detected · Prithvi Highway, Mugling': 'बहुसवारी ठक्कर पहिचान · पृथ्वी राजमार्ग, मुग्लिन',
    'The problem': 'समस्या',
    'Nepal\'s highways are long, isolated, and mostly unwatched.': 'नेपालका राजमार्ग लामो र एकान्त छन्, र धेरैजसो ठाउँमा निगरानी छैन।',
    'No one is watching': 'कसैले निगरानी गरिरहेको छैन',
    'Landslide zones, blind hairpins and fog corridors are long and isolated. Manual patrolling can\'t cover them continuously, day and night.': 'पहिरो क्षेत्र, जोखिमपूर्ण घुम्ती र हुस्सु लाग्ने सडक लामो र एकान्त छन्। पैदल वा सवारी गस्तीले दिनरात निरन्तर निगरानी गर्न सक्दैन।',
    'Reports travel slowly': 'रिपोर्ट ढिलो पुग्छन्',
    'Even when someone spots a crash, the information reaches the right department late — often passed between several people first.': 'कसैले दुर्घटना देखे पनि सूचना सम्बन्धित विभागमा ढिलो पुग्छ, किनकि पहिले धेरै व्यक्तिमार्फत पठाउनुपर्ने हुन्छ।',
    'Detection within seconds means response within minutes, not hours.': 'सेकेन्डमै पहिचान हुँदा घण्टौँ होइन, केही मिनेटमै प्रतिक्रिया दिन सकिन्छ।',
    'From the first frame to the first responder.': 'पहिलो दृश्यदेखि पहिलो उद्धारकर्तासम्म।',
    'Four steps happen automatically, in under a minute, without anyone needing to be watching a screen at that exact moment.': 'कोही पनि त्यही बेला स्क्रिनअगाडि बस्न नपरी एक मिनेटभन्दा कम समयमा चार चरण स्वचालित रूपमा पूरा हुन्छन्।',
    'Rugged, weatherproof cameras on poles along the route': 'मार्गभरिका खम्बामा जडित बलिया, मौसम प्रतिरोधी क्यामेरा',
    'On-device detection — no human needs to be watching': 'उपकरणमै हुने पहिचान — मानिसले निरन्तर हेर्नु पर्दैन',
    'Alerts routed by exact location, not by a phone call': 'फोनबाट होइन, ठ्याक्कै स्थानका आधारमा सतर्कता पठाइन्छ',
    'On-device AI vision active': 'उपकरणमा एआई निगरानी सक्रिय',
    'Watching Prithvi Highway, Mugling': 'पृथ्वी राजमार्ग, मुग्लिनमा निगरानी',
    'Different events need different signals. Detection is tuned for the specific hazards found on Nepali highways and hill routes.': 'फरक घटनाका लागि फरक संकेत आवश्यक हुन्छ। नेपाली राजमार्ग र पहाडी सडकमा देखिने जोखिमअनुसार पहिचान प्रणाली तयार गरिएको छ।',
    'Collisions, overturns and multi-vehicle pile-ups detected within seconds, even on blind curves.': 'जोखिमपूर्ण घुम्तीमा समेत ठक्कर, सवारी पल्टिएको र बहुसवारी दुर्घटना केही सेकेन्डमै पहिचान हुन्छ।',
    'Slope movement and debris dropping onto the carriageway flagged before traffic reaches the zone.': 'सवारीसाधन जोखिम क्षेत्रमा पुग्नुअघि नै पहिरोको चाल र सडकमा खसेको मलबा पहिचान गरिन्छ।',
    'Water level rise and road submergence tracked continuously on low-lying and riverside routes.': 'होचा भूभाग र नदीकिनारका सडकमा पानीको सतह बढेको तथा सडक डुबानमा परेको निरन्तर निगरानी गरिन्छ।',
    'Smoke and flame signatures detected near forest belts, tunnels, fuel stations and parked vehicles.': 'वन क्षेत्र, सुरुङ, इन्धन केन्द्र र रोकिएका सवारीनजिक धुवाँ तथा आगो पहिचान गरिन्छ।',
    'Stalled trucks, fallen trees and broken-down vehicles that choke the carriageway are flagged early.': 'सडक अवरुद्ध गर्ने बिग्रिएका ट्रक, ढलेका रूख र रोकिएका सवारीसाधन समयमै पहिचान गरिन्छ।',
    'One dashboard for every camera and every roadside report.': 'हरेक क्यामेरा र सडकछेउका रिपोर्टका लागि एउटै ड्यासबोर्ड।',
    'Traffic police and disaster response teams monitor live feeds across their assigned stretch and receive citizen reports the instant they\'re filed — mapped by kilometre marker, not buried in a queue.': 'ट्राफिक प्रहरी र विपद् प्रतिक्रिया टोलीले आफ्नो जिम्मेवारीको सडकखण्डको प्रत्यक्ष दृश्य निगरानी गर्छन् र नागरिकका रिपोर्ट प्राप्त हुनासाथ हेर्छन् — रिपोर्टहरू किलोमिटर चिन्हअनुसार नक्सामा देखिन्छन्।',
    'Live camera monitoring across your assigned stretch, 24/7': 'तोकिएको सडकखण्डमा चौबीसै घण्टा प्रत्यक्ष क्यामेरा निगरानी',
    'Combined feed of camera detections and citizen reports': 'क्यामेरा पहिचान र नागरिक रिपोर्टको संयुक्त विवरण',
    'Acknowledge, dispatch and close incidents from one place': 'एउटै ठाउँबाट घटना स्वीकार, टोली परिचालन र घटना बन्द गर्नुहोस्',
    'Empowering witnesses to report incidents instantly and securely.': 'प्रत्यक्षदर्शीलाई तुरुन्त र सुरक्षित रूपमा घटना रिपोर्ट गर्न सक्षम बनाउँदै।',
    'No camera watches every bend. If you witness a collision, a landslide, or a vehicle stuck on a dangerous stretch, विपद्Sathi routes your report directly to the authority covering that road — with your photo as undeniable proof.': 'हरेक घुम्तीमा क्यामेरा हुँदैन। दुर्घटना, पहिरो वा जोखिमपूर्ण सडकमा रोकिएको सवारी देख्नुभयो भने, विपद्Sathi ले तपाईंको तस्बिरसहितको रिपोर्ट सम्बन्धित सडक हेर्ने निकायमा सिधै पठाउँछ।',
    'Track exactly what happened to every report you file': 'तपाईंले पठाउनुभएको प्रत्येक रिपोर्टको अवस्था हेर्नुहोस्',
    'Report in under a minute — location pinned automatically': 'एक मिनेटभन्दा कममा रिपोर्ट गर्नुहोस् — स्थान आफैँ पिन हुन्छ',
    'Track exactly what happened to every report you file': 'तपाईंले पठाउनुभएको प्रत्येक रिपोर्टको अवस्था हेर्नुहोस्',
    'Live on 9 highway camera stretches across Nepal': 'नेपालका ९ राजमार्ग खण्डमा प्रत्यक्ष निगरानी',
    'Alert dispatched': 'सतर्कता पठाइयो',
    'just now': 'भर्खरै',
    'High severity': 'उच्च गम्भीरता',
    'Ambulance notified': 'एम्बुलेन्सलाई खबर गरियो',
    'Every minute of delay compounds': 'ढिलाइको प्रत्येक मिनेटले जोखिम बढाउँछ',
    'Cameras keep watch': 'क्यामेराले निरन्तर निगरानी गर्छन्',
    'AI detects the event': 'एआईले घटना पहिचान गर्छ',
    'Alert routes to the nearest authority': 'सतर्कता नजिकको निकायमा पठाइन्छ',
    'Response is dispatched': 'प्रतिक्रिया टोली परिचालित हुन्छ',
    'For authorities': 'निकायहरूका लागि',
    'Citizen Reporting': 'नागरिक रिपोर्टिङ',
    'Authority log in': 'अधिकारी लग इन',
    'Sign in as an authority': 'अधिकारीका रूपमा साइन इन गर्नुहोस्',
    'Sign up as a citizen': 'नागरिकका रूपमा दर्ता गर्नुहोस्',
    "Don't have an account?": 'खाता छैन?',
    'Forgot Password?': 'पासवर्ड बिर्सनुभयो?',
    'Welcome back.': 'फेरि स्वागत छ।',
    'Log in to continue to your विपद्Sathi account. We will recognize whether you are a citizen or an authority automatically.': 'आफ्नो विपद्Sathi खातामा जान लग इन गर्नुहोस्। तपाईं नागरिक हो वा अधिकारी भन्ने कुरा प्रणालीले आफैँ चिन्नेछ।',
    'Phone number, official email, or Officer/Employee ID': 'फोन नम्बर, आधिकारिक इमेल वा कर्मचारी परिचयपत्र नम्बर',
    'Enter your phone, official email, or ID': 'फोन नम्बर, आधिकारिक इमेल वा परिचयपत्र नम्बर लेख्नुहोस्',
    'Use the details you registered with.': 'दर्ता गर्दा प्रयोग गर्नुभएको विवरण राख्नुहोस्।',
    'Enter your password': 'आफ्नो पासवर्ड लेख्नुहोस्',
    'Show password': 'पासवर्ड देखाउनुहोस्',
    'Hide password': 'पासवर्ड लुकाउनुहोस्',
    'Log In': 'लग इन',
    'Switch language to Nepali': 'भाषा नेपालीमा बदल्नुहोस्',
    'Switch language to English': 'भाषा अंग्रेजीमा बदल्नुहोस्',
    'Please wait...': 'कृपया पर्खनुहोस्...',
    'Search incidents': 'घटनाहरू खोज्नुहोस्',
    'Search Camera ID, location, or source': 'क्यामेरा आईडी, स्थान वा स्रोत खोज्नुहोस्',
    'All': 'सबै',
    'Active': 'सक्रिय',
    'Pending': 'विचाराधीन',
    'Verified': 'पुष्टि भएको',
    'Status': 'अवस्था',
    'Severity': 'गम्भीरता',
    'Type': 'प्रकार',
    'Time': 'समय',
    'View map': 'नक्सा हेर्नुहोस्',
    'Open map': 'नक्सा खोल्नुहोस्',
    'No incidents found': 'कुनै घटना भेटिएन',
    'No reports yet': 'अहिलेसम्म कुनै रिपोर्ट छैन',
    'Response network operational': 'प्रतिक्रिया सञ्जाल सञ्चालनमा छ',
    'A shared line between cameras, citizens, and the authorities who respond.': 'क्यामेरा, नागरिक र प्रतिक्रिया दिने निकायहरूलाई जोड्ने साझा माध्यम।',
  };

  const originalText = new WeakMap();
  const renderedText = new WeakMap();
  const originalAttributes = new WeakMap();
  let language = localStorage.getItem(languageKey) === 'ne' ? 'ne' : 'en';

  const translated = value => {
    const phrase = value.trim();
    if (translations[phrase]) return translations[phrase];
    const reportId = phrase.match(/^Report (RK-\d+)$/i);
    if (reportId) return `रिपोर्ट ${reportId[1]}`;
    const todayTime = phrase.match(/^Today, (\d{1,2}:\d{2}) (AM|PM)$/i);
    if (todayTime) {
      const nepaliDigits = todayTime[1].replace(/\d/g, digit => '०१२३४५६७८९'[Number(digit)]);
      return `आज, ${todayTime[2].toUpperCase() === 'AM' ? 'बिहान' : 'बेलुका'} ${nepaliDigits}`;
    }
    const liveTime = phrase.match(/^LIVE · (\d{2}:\d{2}:\d{2})$/);
    if (liveTime) return `प्रत्यक्ष · ${liveTime[1]}`;
    const onlineStatus = phrase.match(/^(\d+) online · (\d+) offline$/);
    if (onlineStatus) return `${onlineStatus[1]} अनलाइन · ${onlineStatus[2]} अफलाइन`;
    const syncTime = phrase.match(/^Last sync (.+)$/);
    if (syncTime) return `अन्तिम समक्रमण ${syncTime[1]}`;
    return phrase;
  };

  function translateTextNodes() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.parentElement || node.parentElement.closest('script, style, noscript, textarea')) continue;

      let source = originalText.get(node);
      if (source === undefined || node.nodeValue !== renderedText.get(node)) {
        source = node.nodeValue;
        originalText.set(node, source);
      }
      const leading = source.match(/^\s*/)?.[0] || '';
      const trailing = source.match(/\s*$/)?.[0] || '';
      const phrase = source.trim().replace(/\s+/g, ' ');
      const output = language === 'ne' ? translated(phrase) : phrase;
      const nextValue = `${leading}${output}${trailing}`;
      if (node.nodeValue !== nextValue) node.nodeValue = nextValue;
      renderedText.set(node, nextValue);
    }
  }

  function translateAttributes() {
    document.querySelectorAll('[placeholder], [title], [aria-label], [alt]').forEach(element => {
      let values = originalAttributes.get(element);
      if (!values) {
        values = new Map();
        originalAttributes.set(element, values);
      }

      ['placeholder', 'title', 'aria-label', 'alt'].forEach(attribute => {
        if (!element.hasAttribute(attribute)) return;
        let entry = values.get(attribute);
        const current = element.getAttribute(attribute);
        if (!entry || current !== entry.rendered) {
          entry = { source: current, rendered: current };
          values.set(attribute, entry);
        }
        entry.rendered = language === 'ne' ? translated(entry.source) : entry.source;
        element.setAttribute(attribute, entry.rendered);
      });
    });
  }

  function updateButton() {
    const button = document.getElementById('vipsathi-language-toggle');
    if (!button) return;
    const label = language === 'en' ? 'Switch language to Nepali' : 'भाषा अंग्रेजीमा बदल्नुहोस्';
    button.setAttribute('aria-label', label);
    button.title = label;
    button.querySelector('.language-code').textContent = language === 'en' ? 'EN' : 'ने';
  }

  function applyLanguage() {
    document.documentElement.lang = language === 'ne' ? 'ne' : 'en';
    translateTextNodes();
    translateAttributes();
    updateButton();
  }

  function addLanguageButton() {
    if (document.getElementById('vipsathi-language-toggle')) return;
    const host = document.querySelector('.authority-header-right')
      || document.querySelector('.citizen-header-actions')
      || document.querySelector('.nav-actions')
      || document.querySelector('header .nav')
      || document.querySelector('header');
    if (!host) return;

    const button = document.createElement('button');
    button.id = 'vipsathi-language-toggle';
    button.type = 'button';
    button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"></path></svg><span class="language-code"></span>';
    button.addEventListener('click', () => {
      language = language === 'en' ? 'ne' : 'en';
      localStorage.setItem(languageKey, language);
      applyLanguage();
    });

    const style = document.createElement('style');
    style.textContent = '#vipsathi-language-toggle{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-width:56px;height:34px;padding:0 9px;border:1px solid currentColor;border-radius:6px;background:transparent;color:inherit;font-family:inherit;font-size:12px;font-weight:600;line-height:1;cursor:pointer;white-space:nowrap}#vipsathi-language-toggle:hover{background:rgba(127,127,127,.12)}#vipsathi-language-toggle svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}@media(max-width:600px){#vipsathi-language-toggle{min-width:48px;height:32px;padding:0 7px}}';
    document.head.appendChild(style);
    host.appendChild(button);
    updateButton();
  }

  function initialize() {
    addLanguageButton();
    applyLanguage();
    const observer = new MutationObserver(() => {
      translateTextNodes();
      translateAttributes();
      addLanguageButton();
    });
    observer.observe(document.body, { childList: true, characterData: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})();