import { Link } from 'react-router'
import PageHeader from '../PageHeader.jsx'

export default function NotFound() {
  return (
    <>
      <PageHeader title="Page not found" subtitle="This address does not exist in the app." />
      <Link to="/" className="primary">Go to the start page</Link>
    </>
  )
}
