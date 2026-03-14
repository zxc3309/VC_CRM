"""
LinkedIn Profile Scraper using Apify
Searches and extracts LinkedIn profile data for founders
"""

import os
import logging
from typing import Dict, List, Optional
from apify_client import ApifyClient

logger = logging.getLogger(__name__)


class LinkedInSearcher:
    """
    Searches LinkedIn profiles using Apify and extracts structured founder data
    """

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Apify client

        Args:
            api_token: Apify API token. If None, reads from APIFY_API_TOKEN env var
        """
        self.api_token = api_token or os.getenv('APIFY_API_TOKEN')
        if not self.api_token:
            logger.warning("APIFY_API_TOKEN not set. LinkedIn scraping will be disabled.")
            self.client = None
        else:
            self.client = ApifyClient(self.api_token)

    async def search_founder_profile(
        self,
        founder_name: str,
        company_name: str,
        max_results: int = 10
    ) -> Optional[Dict]:
        """
        Search for a founder's LinkedIn profile using their name and company

        Args:
            founder_name: Name of the founder to search for
            company_name: Company name to help identify the correct person
            max_results: Maximum number of search results to retrieve (default: 5)

        Returns:
            Dict containing the LinkedIn profile data, or None if not found/failed
        """
        if not self.client:
            logger.warning("Apify client not initialized. Skipping LinkedIn search.")
            return None

        try:
            # Split founder name into first and last name
            name_parts = founder_name.strip().split()
            first_name = name_parts[0] if name_parts else founder_name
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            logger.info(f"Searching LinkedIn for: {first_name} {last_name} at {company_name}")

            # Run input for the Apify Actor
            # Using harvestapi/linkedin-profile-search-by-name for precise name-based search
            run_input = {
                "firstName": first_name,
                "lastName": last_name,
                "maxItems": max_results,
                "profileScraperMode": "Full",
            }

            # Execute the Actor
            logger.info("Running Apify LinkedIn Profile Search By Name Actor...")
            run = self.client.actor("harvestapi/linkedin-profile-search-by-name").call(
                run_input=run_input
            )

            # Get results from the dataset
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                logger.error("No dataset ID returned from Apify run")
                return None

            results = list(self.client.dataset(dataset_id).iterate_items())

            if not results:
                logger.warning(f"No LinkedIn profiles found for: {first_name} {last_name}")
                return None

            logger.info(f"Found {len(results)} LinkedIn profile(s)")

            # Validate and select the best matching profile
            best_match = self._validate_founder(results, company_name, founder_name)

            if best_match:
                logger.info(f"Selected profile: {best_match.get('publicIdentifier', 'unknown')}")
            else:
                logger.warning("No matching profile found after validation")

            return best_match

        except Exception as e:
            logger.error(f"Error searching LinkedIn profile: {e}", exc_info=True)
            return None

    def _validate_founder(
        self,
        results: List[Dict],
        company_name: str,
        founder_name: str
    ) -> Optional[Dict]:
        """
        Validate search results and select the best matching founder profile

        Strategy:
        1. Check if current company matches
        2. Check if job title contains founder/CEO keywords
        3. Check if name matches closely
        4. Fallback to first result if no perfect match

        Args:
            results: List of LinkedIn profile search results
            company_name: Expected company name
            founder_name: Expected founder name

        Returns:
            Best matching profile or None
        """
        if not results:
            return None

        company_name_lower = company_name.lower()
        founder_name_lower = founder_name.lower()
        founder_keywords = ['founder', 'co-founder', 'ceo', 'chief executive']

        # Score each result
        scored_results = []

        for profile in results:
            score = 0

            # Check full name match (new actor uses firstName + lastName)
            full_name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip().lower()
            if founder_name_lower in full_name or full_name in founder_name_lower:
                score += 10

            # Check current position/headline
            headline = profile.get('headline', '').lower()
            if company_name_lower in headline:
                score += 5

            # Check if title contains founder keywords
            if any(keyword in headline for keyword in founder_keywords):
                score += 3

            # Check experiences for company match (new actor uses 'experience' list)
            experiences = profile.get('experience', [])
            for exp in experiences:
                exp_company = exp.get('companyName', '').lower()
                exp_title = exp.get('position', '').lower()

                if company_name_lower in exp_company:
                    score += 5
                    # Extra points if it's a founder role at this company
                    if any(keyword in exp_title for keyword in founder_keywords):
                        score += 3

            scored_results.append((score, profile))

        # Sort by score (descending)
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Log scoring results
        for i, (score, profile) in enumerate(scored_results[:3]):
            full_name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
            logger.info(
                f"Profile {i+1}: {full_name} - "
                f"Score: {score} - "
                f"Headline: {profile.get('headline', 'N/A')}"
            )

        # Return the highest scoring result if score > 0
        if scored_results and scored_results[0][0] > 0:
            return scored_results[0][1]

        # Fallback to first result if no good match
        logger.info("No high-confidence match found, using first result as fallback")
        return results[0] if results else None

    def extract_experience_data(self, profile: Dict) -> Dict:
        """
        Extract and format experience data from a LinkedIn profile

        Args:
            profile: Raw LinkedIn profile data from Apify

        Returns:
            Formatted dict with extracted data
        """
        if not profile:
            return {}

        # Extract positions/experience (new actor uses 'experience' list directly)
        positions_data = profile.get('experience', [])
        formatted_experience = []

        for pos in positions_data:
            exp_entry = {
                'company': pos.get('companyName', ''),
                'role': pos.get('position', ''),
                'duration': pos.get('duration', ''),
                'description': pos.get('description', '')
            }
            formatted_experience.append(exp_entry)

        # Extract education (new actor uses 'education' list directly)
        education_data = profile.get('education', [])
        formatted_education = []

        for edu in education_data:
            edu_entry = {
                'school': edu.get('schoolName', ''),
                'degree': edu.get('degree', ''),
                'field': edu.get('fieldOfStudy', ''),
                'duration': edu.get('period', '')
            }
            formatted_education.append(edu_entry)

        # Extract skills (new actor uses 'skills' list with 'name' field)
        skills_data = profile.get('skills', [])
        skills_list = []
        for skill in skills_data:
            if isinstance(skill, dict):
                name = skill.get('name', '')
            elif isinstance(skill, str):
                name = skill
            else:
                continue
            if name:
                skills_list.append(name)

        # Build full name from firstName + lastName
        full_name = f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()

        # Extract location text
        location = profile.get('location', {})
        if isinstance(location, dict):
            location_text = location.get('linkedinText', '') or location.get('parsed', {}).get('text', '')
        else:
            location_text = str(location) if location else ''

        return {
            'name': full_name,
            'title': profile.get('headline', ''),
            'location': location_text,
            'linkedin_url': profile.get('linkedinUrl', ''),
            'public_identifier': profile.get('publicIdentifier', ''),
            'followers': profile.get('followerCount'),
            'connections': profile.get('connectionsCount'),
            'about': profile.get('about', ''),
            'experience': formatted_experience,
            'education': formatted_education,
            'skills': skills_list[:10],  # Top 10 skills
            'profile_picture': profile.get('photo', '')
        }
