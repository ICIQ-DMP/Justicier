# justicier - Automated employee justifications
# Copyright (C) 2026  Aleix Mariné Tena (AleixMT), Carles de la Cuadra
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Error handler entry point: marks the request as failed and uploads the admin log."""

from arguments import parse_arguments
from mail import send_mail_authenticated, build_admin_error_mail_body
from sharepoint import (
    update_list_item_field,
)
from secret import read_secret
from defines import (
    SharepointListFieldWorkflowState,
    SharepointListFields,
)


def main() -> None:
    """Mark a request as failed in SharePoint and upload the admin log."""
    args = parse_arguments()
    update_list_item_field(
        args.request,
        {
            SharepointListFields.WORKFLOW_STATE.value: SharepointListFieldWorkflowState.ERROR.value
        },
    )
    send_mail_authenticated(
        read_secret("SMTP_ADMIN_EMAIL"),
        "El workflow al Jenkins ha fallat",
        build_admin_error_mail_body(args.request),
    )


if __name__ == "__main__":
    main()
