export default function UserPage({ params }: { params: { id: string } }) {
  return <main>User {params.id}</main>;
}
