export interface CourseInstructor {
	creation: string
	name: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Instructor : Link - User	*/
	instructor?: string
	/**	Invitation Status : Select	*/
	invitation_status?: 'Accepted' | 'Pending'
	/**	Visible : Check	*/
	is_visible?: 0 | 1
	/**	Manage course : Check	*/
	can_manage_course?: 0 | 1
	/**	Captions : Check	*/
	can_manage_captions?: 0 | 1
	/**	Performance : Check	*/
	can_view_performance?: 0 | 1
	/**	Q&A : Check	*/
	can_manage_qa?: 0 | 1
	/**	Assignments : Check	*/
	can_manage_assignments?: 0 | 1
	/**	Reviews : Check	*/
	can_manage_reviews?: 0 | 1
}
