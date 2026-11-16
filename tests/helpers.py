from jobwatch.models import Job


def job(key="A:1", title="Software Engineer", location="Hyderabad", posted_at=None, company="A"):
    return Job(key=key, company=company, title=title, location=location,
               url=f"https://x/{key}", posted_at=posted_at)
